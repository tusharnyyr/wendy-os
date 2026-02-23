# services/analytics_service.py
# New in Wendy OS v0.4
# Responsibilities: Compute weekly structured analytics per user

from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import ActivityLog, WeeklySummary


def get_week_start(ref_date: Optional[date] = None) -> date:
    """Return the Monday of the current (or reference) week."""
    d = ref_date or date.today()
    return d - timedelta(days=d.weekday())


def compute_weekly_analytics(user_id: str, db: Session, week_start: Optional[date] = None) -> dict:
    """
    Query activity logs for the given week and return structured analytics.
    Returns a dict with totals, category breakdown, streak info, and trends.
    """
    start = week_start or get_week_start()
    end = start + timedelta(days=6)

    logs = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user_id,
            ActivityLog.log_date >= start,
            ActivityLog.log_date <= end,
        )
        .all()
    )

    # Total minutes
    total_minutes = sum(log.duration_minutes for log in logs)

    # Category breakdown
    category_totals: dict[str, int] = {}
    for log in logs:
        category_totals[log.category] = (
            category_totals.get(log.category, 0) + log.duration_minutes
        )

    # Active days (days with at least one log)
    active_days = len({log.log_date for log in logs})

    # Streak calculation — consecutive days ending at end of week
    streak = _compute_streak(user_id, db, end)

    return {
        "week_start": str(start),
        "week_end": str(end),
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "active_days": active_days,
        "category_breakdown": category_totals,
        "log_count": len(logs),
        "streak_days": streak,
    }


def _compute_streak(user_id: str, db: Session, up_to: date) -> int:
    """Count consecutive active days ending at up_to."""
    streak = 0
    current = up_to
    while True:
        has_log = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user_id,
                ActivityLog.log_date == current,
            )
            .first()
        )
        if not has_log:
            break
        streak += 1
        current -= timedelta(days=1)
    return streak


def summary_exists_for_week(user_id: str, week_start: date, db: Session) -> bool:
    """Idempotency check — returns True if summary already exists for this week."""
    return (
        db.query(WeeklySummary)
        .filter(
            WeeklySummary.user_id == user_id,
            WeeklySummary.week_start == week_start,
        )
        .first()
        is not None
    )


def save_weekly_summary(
    user_id: str,
    week_start: date,
    structured_summary: dict,
    narrative: str,
    suggestion: dict,
    db: Session,
) -> WeeklySummary:
    """Persist weekly summary to DB."""
    record = WeeklySummary(
        user_id=user_id,
        week_start=week_start,
        structured_summary=structured_summary,
        narrative=narrative,
        suggestion=suggestion,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def fetch_weekly_summary(user_id: str, week_start: date, db: Session) -> Optional[WeeklySummary]:
    """Retrieve stored weekly summary."""
    return (
        db.query(WeeklySummary)
        .filter(
            WeeklySummary.user_id == user_id,
            WeeklySummary.week_start == week_start,
        )
        .first()
    )