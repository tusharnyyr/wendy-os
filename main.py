"""
Wendy OS v0.4 - Main FastAPI Application
Personal AI automation assistant with event-driven automation layer.

v0.4 Changes:
- Telegram user resolution via telegram_user_id
- /generate-weekly-summary endpoint (cron-triggered by n8n)
- /weekly-summary-segment endpoint (inline button handler)
- /analytics/drift-status endpoint (daily cron for proactive alerts)
- /users/link-telegram endpoint (one-time Telegram account linking)
- verify_cron_token dependency for internal endpoint protection
"""
import os
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uvicorn
from datetime import datetime

from database import get_db, init_db
from database.models import User
from services import (
    AuthService,
    IntentRouter,
    LoggingService,
    EventBus
)
from services.chat_service import ChatService
from services import weekly_summary_service
from services import drift_service

# Initialize FastAPI app
app = FastAPI(
    title="Wendy",
    description="Personal AI Automation Assistant - v0.4 (Telegram + Analytics + Drift Detection)",
    version="0.4.0"
)

# Initialize services
logging_service = LoggingService()
event_bus = EventBus()


# ── Request / Response Models ─────────────────────────────────────────────────

class MessageRequest(BaseModel):
    """Incoming message — supports both API token and Telegram sources."""
    message: str
    phone_number: Optional[str] = None       # WhatsApp interface
    source: Optional[str] = "api"            # "api" | "telegram"
    telegram_user_id: Optional[str] = None   # v0.4: Telegram sender ID


class MessageResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class SegmentRequest(BaseModel):
    telegram_user_id: str
    segment: str  # overview | trends | categories | streak | suggestion


class TelegramLinkRequest(BaseModel):
    api_token: str          # Wendy API token to identify the user
    telegram_user_id: str   # Telegram sender ID (from.id)
    telegram_chat_id: str   # Telegram chat ID (message.chat.id)


# ── Cron Token Auth ───────────────────────────────────────────────────────────

WENDY_CRON_TOKEN = os.getenv("WENDY_CRON_TOKEN", "")


def verify_cron_token(x_wendy_cron_token: str = Header(...)):
    """Protect internal cron endpoints. Only n8n should call these."""
    if not WENDY_CRON_TOKEN or x_wendy_cron_token != WENDY_CRON_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid cron token.")


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    print("🚀 Starting Wendy v0.4...")
    init_db()
    print("✅ Database initialized")

    from dotenv import load_dotenv
    load_dotenv()

    n8n_url = os.getenv("N8N_WEBHOOK_URL")
    if n8n_url and n8n_url.strip():
        print("✅ n8n webhook configured")
    else:
        print("ℹ️  n8n webhook not configured (events stored but not dispatched)")

    cron_token = os.getenv("WENDY_CRON_TOKEN")
    if cron_token and cron_token.strip():
        print("✅ Cron token configured")
    else:
        print("⚠️  WENDY_CRON_TOKEN not set — /generate-weekly-summary will reject all requests")


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Wendy v0.4"}


# ── Main Message Endpoint ─────────────────────────────────────────────────────

@app.post("/message", response_model=MessageResponse)
def handle_message(
    request: MessageRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Universal message endpoint.
    Supports three auth paths:
      1. source=telegram  → resolve user from telegram_user_id
      2. phone_number     → resolve user from WhatsApp number
      3. Bearer token     → resolve user from API token
    """
    user = None

    # Path 1: Telegram
    if request.source == "telegram" and request.telegram_user_id:
        user = db.query(User).filter(
            User.telegram_user_id == request.telegram_user_id
        ).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Telegram user not registered. Use /users/link-telegram first."
            )

    # Path 2: WhatsApp phone number
    elif request.phone_number:
        user = AuthService.resolve_user_from_phone(db, request.phone_number)

    # Path 3: API Bearer token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        user = AuthService.resolve_user_from_token(db, token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found. Provide valid credentials."
        )

    # Route by intent
    intent_result = IntentRouter.detect_intent(request.message)
    intent = intent_result["intent"]
    payload = intent_result["payload"]

    if intent == "log":
        return handle_log_intent(db, user, payload)
    else:
        return handle_chat_intent(db, user, payload)


def handle_log_intent(db: Session, user, log_text: str) -> MessageResponse:
    result = logging_service.create_log(db, user, log_text)

    if not result["success"]:
        return MessageResponse(
            success=False,
            message=f"❌ Failed to create log: {result['error']}"
        )

    log = result["log"]
    weekly_total = result["weekly_total"]
    streak = result["streak"]

    hours = log.duration_minutes // 60
    minutes = log.duration_minutes % 60
    duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    weekly_hours = weekly_total // 60
    weekly_mins = weekly_total % 60
    weekly_str = f"{weekly_hours}h {weekly_mins}m" if weekly_hours > 0 else f"{weekly_mins}m"

    response_message = (
        f"✅ Logged: {log.activity_name}\n"
        f"📂 Category: {log.category.value}\n"
        f"⏱️ Duration: {duration_str}\n"
        f"📊 This week: {weekly_str}\n"
        f"🔥 Streak: {streak} days"
    )

    return MessageResponse(
        success=True,
        message=response_message,
        data={
	    "intent": "log",
            "log_id": str(log.id),
            "activity_name": log.activity_name,
            "category": log.category.value,
            "duration_minutes": log.duration_minutes,
            "weekly_total": weekly_total,
            "streak": streak
        }
    )


def handle_chat_intent(db: Session, user, message: str) -> MessageResponse:
    try:
        chat_service = ChatService(db)
        response = chat_service.handle_chat(user.id, message)
        return MessageResponse(success=True, message=response, data={"intent": "chat"})
    except Exception as e:
        print(f"Chat service error: {str(e)}")
        return MessageResponse(
            success=False,
            message="Wendy is temporarily unavailable. Please try again."
        )


# ── User Management ───────────────────────────────────────────────────────────

@app.post("/users/create")
def create_user(
    name: str,
    email: str,
    whatsapp_number: Optional[str] = None,
    api_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new user."""
    try:
        user = AuthService.create_user(
            db=db,
            name=name,
            email=email,
            whatsapp_number=whatsapp_number,
            api_token=api_token
        )
        return {
            "success": True,
            "user_id": str(user.id),
            "name": user.name,
            "email": user.email
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/users/link-telegram")
def link_telegram(request: TelegramLinkRequest, db: Session = Depends(get_db)):
    """
    Link a Telegram identity to an existing Wendy user account.
    Call this once per user to enable Telegram messaging and proactive alerts.
    """
    user = db.query(User).filter(User.api_token == request.api_token).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Check your API token.")

    user.telegram_user_id = request.telegram_user_id
    user.telegram_chat_id = request.telegram_chat_id
    db.commit()

    return {
        "success": True,
        "message": f"Telegram linked for {user.name}. You can now use Wendy via Telegram.",
        "user_id": str(user.id)
    }


# ── Weekly Summary Endpoints ──────────────────────────────────────────────────

@app.post("/generate-weekly-summary", dependencies=[Depends(verify_cron_token)])
def generate_weekly_summary_endpoint(db: Session = Depends(get_db)):
    """
    Called by n8n Cron Node every Sunday at 20:00.
    Generates weekly summary for all users. Idempotent — safe to call multiple times.
    Requires X-WENDY-CRON-TOKEN header.
    """
    users = db.query(User).all()
    results = []

    for user in users:
        result = weekly_summary_service.generate_weekly_summary(str(user.id), db)
        results.append(result)

    return {
        "status": "complete",
        "processed": len(results),
        "results": results
    }


@app.post("/weekly-summary-segment")
def get_summary_segment(request: SegmentRequest, db: Session = Depends(get_db)):
    """
    Called by n8n when user clicks an inline Telegram button.
    Returns one section of the stored weekly summary. No recomputation.
    Segments: overview | trends | categories | streak | suggestion
    """
    user = db.query(User).filter(
        User.telegram_user_id == request.telegram_user_id
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Telegram user not registered.")

    result = weekly_summary_service.get_summary_segment(str(user.id), request.segment, db)
    return result


# ── Analytics / Drift Detection ───────────────────────────────────────────────

@app.get("/analytics/drift-status", dependencies=[Depends(verify_cron_token)])
def get_drift_status(db: Session = Depends(get_db)):
    """
    Called by n8n Daily Drift Check cron at 21:00.
    Returns risk assessment for all users.
    n8n filters risk_flag=True and sends proactive Telegram alerts.
    Requires X-WENDY-CRON-TOKEN header.
    """
    users = db.query(User).all()
    report = drift_service.get_drift_report(users, db)
    at_risk = sum(1 for u in report if u["risk_flag"])

    return {
        "users": report,
        "evaluated_at": datetime.utcnow().isoformat(),
        "at_risk_count": at_risk
    }


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )