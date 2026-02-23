"""
Drift Detection Service for Wendy OS v0.4
Computes daily risk flags per user for n8n proactive alerts.
"""
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from database.models import ActivityLog, User

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────

DECLINE_THRESHOLD = 0.70    # <70% of baseline = productivity decline
MIN_BASELINE_MINUTES = 30   # Ignore baseline if user has very little history


# ── Core Queries ──────────────────────────────────────────────────────────────

def compute_daily_average(user_id: str, db: Session, days: int, up_to: date) -> float:
    """Average daily minutes over last N days (active days only)."""
    start = up_to - timedelta(days=days - 1)

    total = (
        db.query(func.sum(ActivityLog.duration_minutes))
        .filter(
            ActivityLog.user_id == user_id,
            ActivityLog.date >= start,
            ActivityLog.date <= up_to,
        )
        .scalar()
    ) or 0

    active_days = (
        db.query(func.count(func.distinct(ActivityLog.date)))
        .filter(
            ActivityLog.user_id == user_id,
            ActivityLog.date >= start,
            ActivityLog.date <= up_to,
        )
        .scalar()
    ) or 0

    if active_days == 0:
        return 0.0

    return total / active_days


def has_logged_today(user_id: str, db: Session, today: date) -> bool:
    """Check if user has any log entry for today."""
    return (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user_id,
            ActivityLog.date == today,
        )
        .first()
        is not None
    )


def compute_current_streak(user_id: str, db: Session, today: date) -> int:
    """Count consecutive days with at least one log, ending at today."""
    streak = 0
    current = today
    while True:
        has_log = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user_id,
                ActivityLog.date == current,
            )
            .first()
        )
        if not has_log:
            break
        streak += 1
        current -= timedelta(days=1)
    return streak


def get_recent_total_minutes(user_id: str, db: Session, days: int, today: date) -> int:
    """Total minutes logged over the last N days."""
    start = today - timedelta(days=days - 1)
    result = (
        db.query(func.sum(ActivityLog.duration_minutes))
        .filter(
            ActivityLog.user_id == user_id,
            ActivityLog.date >= start,
            ActivityLog.date <= today,
        )
        .scalar()
    )
    return result or 0


# ── Risk Evaluation ───────────────────────────────────────────────────────────

def evaluate_user_risk(user_id: str, db: Session) -> dict:
    """
    Run full drift analysis for one user.

    Risk priority:
      1. no_log_today       — streak exists, nothing logged yet today
      2. low_consistency    — no streak, no log today
      3. productivity_decline — output <70% of 14-day baseline
      4. None               — user is on track
    """
    today = date.today()

    # 14-day baseline (exclude today)
    baseline_ref = today - timedelta(days=1)
    baseline_avg = compute_daily_average(user_id, db, days=14, up_to=baseline_ref)

    # Last 3 days total and daily average
    recent_total = get_recent_total_minutes(user_id, db, days=3, today=today)
    recent_avg = recent_total / 3

    # Streak and today check
    streak = compute_current_streak(user_id, db, today)
    logged_today = has_logged_today(user_id, db, today)

    # Determine risk
    risk_flag = False
    risk_type = None

    if not logged_today and streak > 0:
        risk_flag = True
        risk_type = "no_log_today"

    elif not logged_today and streak == 0:
        risk_flag = True
        risk_type = "low_consistency"

    elif (
        baseline_avg >= MIN_BASELINE_MINUTES
        and recent_avg < baseline_avg * DECLINE_THRESHOLD
    ):
        risk_flag = True
        risk_type = "productivity_decline"

    return {
        "user_id": str(user_id),
        "risk_flag": risk_flag,
        "risk_type": risk_type,
        "streak_days": streak,
        "logged_today": logged_today,
        "baseline_minutes": round(baseline_avg, 1),
        "recent_minutes": recent_total,
        "recent_daily_avg": round(recent_avg, 1),
    }


# ── Multi-user Report ─────────────────────────────────────────────────────────

def get_drift_report(users: list, db: Session) -> list:
    """
    Evaluate all users. Returns list of risk dicts including chat_id.
    """
    results = []
    for user in users:
        try:
            risk = evaluate_user_risk(str(user.id), db)
            risk["chat_id"] = user.telegram_chat_id or None
            results.append(risk)
        except Exception as e:
            logger.error(f"Drift evaluation failed for user {user.id}: {e}")
    return results
