"""
Logging Service for Wendy v0.3
Handles activity log creation, weekly totals, and streak detection.

v0.3 Changes:
- Emits structured "log_created" events via EventBus
- Integrated with new event_bus.emit_event() method
"""
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Dict, Any
import uuid

from database.models import ActivityLog, User, CategoryEnum
from services.ai_adapter import AIAdapter
from services.event_bus import EventBus


class LoggingService:
    """Service for managing activity logs."""

    def __init__(self):
        """Initialize logging service with AI adapter and event bus."""
        self.ai_adapter = AIAdapter()
        self.event_bus = EventBus()  # v0.3: Added event bus

    def create_log(
        self,
        db: Session,
        user: User,
        log_text: str
    ) -> Dict[str, Any]:
        """
        Create activity log from natural language input.
        
        Workflow:
        1. Parse log text with AI
        2. Validate parsed data
        3. Save to database
        4. Compute weekly total
        5. Compute streak
        6. Emit "log_created" event (v0.3 NEW)
        7. Return confirmation data
        
        Args:
            db: Database session
            user: User object
            log_text: Natural language log description
        
        Returns:
            Dictionary with:
                - success: bool
                - log: ActivityLog object (if success=True)
                - weekly_total: int (total minutes this week)
                - streak: int (consecutive days logged)
                - error: str (if success=False)
        """
        # Step 1: Parse with AI
        parse_result = self.ai_adapter.parse_log_to_json(log_text)
        
        if not parse_result["success"]:
            return {
                "success": False,
                "error": parse_result["error"]
            }
        
        parsed_data = parse_result["data"]
        
        # Step 2: Create ActivityLog object
        try:
            activity_log = ActivityLog(
                id=uuid.uuid4(),
                user_id=user.id,
                date=date.today(),
                activity_name=parsed_data["activity_name"],
                category=CategoryEnum[parsed_data["category"].upper()],
                duration_minutes=int(parsed_data["duration_minutes"]),
                notes=parsed_data["notes"] if parsed_data["notes"] else None
            )
            
            # Step 3: Save to database
            db.add(activity_log)
            db.commit()
            db.refresh(activity_log)
            
            # Step 4: Compute weekly total
            weekly_total = self.get_weekly_total(db, user.id)
            
            # Step 5: Compute streak
            streak = self.compute_streak(db, user.id)
            
            # Step 6: v0.3 NEW - Emit "log_created" event
            event_result = self.event_bus.emit_event(
                db=db,
                event_type="log_created",
                user_id=str(user.id),
                source="logging_service",
                payload={
                    "log_id": str(activity_log.id),
                    "activity_name": activity_log.activity_name,
                    "category": activity_log.category.value,
                    "duration_minutes": activity_log.duration_minutes,
                    "date": activity_log.date.isoformat(),
                    "weekly_total": weekly_total,
                    "streak": streak
                }
            )
            
            # Log event emission result (for debugging)
            if not event_result["success"]:
                print(f"Warning: Event emission failed: {event_result.get('error')}")
            
            return {
                "success": True,
                "log": activity_log,
                "weekly_total": weekly_total,
                "streak": streak
            }
        
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": f"Database error: {str(e)}"
            }

    def get_weekly_total(self, db: Session, user_id: uuid.UUID) -> int:
        """
        Calculate total minutes logged this week (Monday to Sunday).
        
        Args:
            db: Database session
            user_id: User's UUID
        
        Returns:
            Total duration in minutes for current week
        """
        # Get current week's Monday
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        # Query logs from Monday onwards
        logs = db.query(ActivityLog).filter(
            ActivityLog.user_id == user_id,
            ActivityLog.date >= monday
        ).all()
        
        # Sum durations
        total_minutes = sum(log.duration_minutes for log in logs)
        
        return total_minutes

    def compute_streak(self, db: Session, user_id: uuid.UUID) -> int:
        """
        Compute consecutive days with at least one log entry.
        
        Counts backwards from today until finding a day with no logs.
        
        Args:
            db: Database session
            user_id: User's UUID
        
        Returns:
            Number of consecutive days with activity logs
        
        Examples:
            - Logged today, yesterday, day before → streak = 3
            - Logged today, skipped yesterday → streak = 1
            - No logs today → streak = 0
        """
        streak = 0
        current_date = date.today()
        
        # Check backwards day by day
        while True:
            # Check if there's at least one log on current_date
            log_exists = db.query(ActivityLog).filter(
                ActivityLog.user_id == user_id,
                ActivityLog.date == current_date
            ).first()
            
            if log_exists:
                streak += 1
                # Move to previous day
                current_date = current_date - timedelta(days=1)
            else:
                # Streak broken
                break
            
            # Safety limit: don't go back more than 365 days
            if streak >= 365:
                break
        
        return streak

    def get_user_logs(
        self,
        db: Session,
        user_id: uuid.UUID,
        limit: int = 10
    ) -> list:
        """
        Get recent activity logs for user.
        
        Args:
            db: Database session
            user_id: User's UUID
            limit: Maximum number of logs to return
        
        Returns:
            List of ActivityLog objects, newest first
        """
        logs = db.query(ActivityLog).filter(
            ActivityLog.user_id == user_id
        ).order_by(
            ActivityLog.created_at.desc()
        ).limit(limit).all()
        
        return logs

    def get_daily_summary(
        self,
        db: Session,
        user_id: uuid.UUID,
        target_date: date = None
    ) -> Dict[str, Any]:
        """
        Get summary of logs for a specific date.
        
        Args:
            db: Database session
            user_id: User's UUID
            target_date: Date to summarize (defaults to today)
        
        Returns:
            Dictionary with:
                - date: date
                - total_minutes: int
                - log_count: int
                - logs: list of ActivityLog objects
        """
        if target_date is None:
            target_date = date.today()
        
        logs = db.query(ActivityLog).filter(
            ActivityLog.user_id == user_id,
            ActivityLog.date == target_date
        ).all()
        
        total_minutes = sum(log.duration_minutes for log in logs)
        
        return {
            "date": target_date,
            "total_minutes": total_minutes,
            "log_count": len(logs),
            "logs": logs
        }
