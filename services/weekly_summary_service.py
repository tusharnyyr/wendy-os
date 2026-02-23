# services/weekly_summary_service.py
# New in Wendy OS v0.4
# Orchestrates analytics + suggestion + AI narrative + event emission

import os
from datetime import date
from sqlalchemy.orm import Session
from groq import Groq

from services import analytics_service, suggestion_engine
from services.event_bus import emit_event


def generate_ai_narrative(structured_summary: dict) -> str:
    """Ask AI to write a short narrative paragraph summarising the week."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Weekly summary computed."

    try:
        client = Groq(api_key=api_key)
        prompt = (
            f"You are Wendy. Write a short, friendly 2-3 sentence narrative "
            f"summarising this user's week based on the data: {structured_summary}. "
            f"Be encouraging and specific about what they did."
        )
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[weekly_summary_service] Narrative AI failed: {e}")
        return "Weekly summary computed."


def generate_weekly_summary(user_id: str, db: Session) -> dict:
    """
    Full pipeline for one user:
    1. Idempotency check
    2. Compute analytics
    3. Generate suggestion
    4. Generate narrative
    5. Save to DB
    6. Emit event
    Returns result dict.
    """
    week_start = analytics_service.get_week_start()

    # Idempotency — skip if already generated this week
    if analytics_service.summary_exists_for_week(user_id, week_start, db):
        return {
            "status": "skipped",
            "reason": "Summary already exists for this week",
            "week_start": str(week_start),
            "user_id": user_id,
        }

    # Step 1: Compute structured analytics
    structured = analytics_service.compute_weekly_analytics(user_id, db, week_start)

    # Step 2: Generate suggestion (rule + AI hybrid)
    suggestion = suggestion_engine.generate_suggestion(structured)

    # Step 3: Generate AI narrative
    narrative = generate_ai_narrative(structured)

    # Step 4: Save summary to DB
    record = analytics_service.save_weekly_summary(
        user_id=user_id,
        week_start=week_start,
        structured_summary=structured,
        narrative=narrative,
        suggestion=suggestion,
        db=db,
    )

    # Step 5: Emit event
    emit_event(
        event_type="weekly_summary_generated",
        user_id=user_id,
        source="weekly_summary_service",
        payload={
            "week_start": str(week_start),
            "total_minutes": structured["total_minutes"],
            "active_days": structured["active_days"],
            "suggestion_type": suggestion["type"],
        },
        db=db,
    )

    return {
        "status": "generated",
        "week_start": str(week_start),
        "user_id": user_id,
        "summary_id": str(record.id),
    }


def get_summary_segment(user_id: str, segment: str, db: Session) -> dict:
    """
    Retrieve a specific segment of the stored weekly summary.
    Segments: overview, trends, categories, streak, suggestion
    """
    week_start = analytics_service.get_week_start()
    record = analytics_service.fetch_weekly_summary(user_id, week_start, db)

    if not record:
        return {"error": "No summary found for this week. Please generate one first."}

    s = record.structured_summary

    segments = {
        "overview": {
            "segment": "overview",
            "total_hours": s.get("total_hours"),
            "total_minutes": s.get("total_minutes"),
            "active_days": s.get("active_days"),
            "log_count": s.get("log_count"),
            "narrative": record.narrative,
        },
        "trends": {
            "segment": "trends",
            "active_days": s.get("active_days"),
            "total_hours": s.get("total_hours"),
            "week_start": s.get("week_start"),
            "week_end": s.get("week_end"),
        },
        "categories": {
            "segment": "categories",
            "category_breakdown": s.get("category_breakdown", {}),
        },
        "streak": {
            "segment": "streak",
            "streak_days": s.get("streak_days"),
            "active_days": s.get("active_days"),
        },
        "suggestion": {
            "segment": "suggestion",
            "suggestion": record.suggestion,
        },
    }

    return segments.get(segment, {"error": f"Unknown segment '{segment}'. Valid: {list(segments.keys())}"})