"""
Event Bus for Wendy v0.3
Handles event emission, storage, and webhook notifications.

v0.3 Changes:
- Structured event validation (event_type, source, payload)
- Separate n8n adapter integration
- Clean create/save/dispatch abstraction
- Maintains backward compatibility with v0.2
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional, Literal
import uuid
import logging
from pydantic import BaseModel, Field, validator

from database.models import Event, User

# Configure logging
logger = logging.getLogger(__name__)


# v0.3: Structured Event Model
class EventModel(BaseModel):
    """
    Structured event model following v0.3 specification.
    
    All events in Wendy OS must follow this structure.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    user_id: str
    source: Literal["logging_service", "chat_service"]
    payload: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Ensure user_id is valid UUID format"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"Invalid user_id format: {v}")
        return v
    
    @validator('event_type')
    def validate_event_type(cls, v):
        """Ensure event_type is one of allowed types in v0.3"""
        allowed_types = ['log_created', 'chat_message_created']
        if v not in allowed_types:
            raise ValueError(f"Invalid event_type: {v}. Must be one of {allowed_types}")
        return v


class EventBus:
    """Event bus for tracking and notifying system events."""

    def __init__(self):
        """Initialize event bus."""
        pass

    # v0.2 COMPATIBILITY METHOD (keep for backward compatibility)
    def emit(
        self,
        db: Session,
        user: User,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Emit an event: save to database and optionally send webhook.
        
        v0.2 COMPATIBILITY METHOD - Still works!
        For new code, use emit_event() instead.
        
        Args:
            db: Database session
            user: User object
            event_type: Type of event (e.g., "log_created", "user_registered")
            payload: Event data (will be stored as JSONB)
        
        Returns:
            Dictionary with:
                - success: bool
                - event_id: UUID (if success=True)
                - webhook_sent: bool
                - error: str (if success=False)
        """
        try:
            # Save event to database
            event = Event(
                id=uuid.uuid4(),
                user_id=user.id,
                event_type=event_type,
                payload=payload,
                created_at=datetime.utcnow()
            )
            
            db.add(event)
            db.commit()
            db.refresh(event)
            
            # Send webhook (if configured)
            webhook_sent = self._dispatch_to_n8n(event)
            
            return {
                "success": True,
                "event_id": event.id,
                "webhook_sent": webhook_sent
            }
        
        except Exception as e:
            db.rollback()
            logger.error(f"Event emission failed: {str(e)}")
            return {
                "success": False,
                "error": f"Event emission failed: {str(e)}"
            }

    # v0.3 NEW METHOD (structured events)
    def emit_event(
        self,
        db: Session,
        event_type: str,
        user_id: str,
        source: Literal["logging_service", "chat_service"],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        v0.3: Emit structured event with validation.
        
        This is the new v0.3 method for emitting events.
        
        Workflow:
        1. Create structured event (validate)
        2. Save to database (required)
        3. Dispatch to n8n (optional, non-blocking)
        
        Args:
            db: Database session
            event_type: Type of event (log_created, chat_message_created)
            user_id: UUID string of the user
            source: Service generating the event
            payload: Event data
            
        Returns:
            Dict with success, event_id, and dispatched status
        """
        # Step 1: Create and validate event
        event_model = self._create_event(event_type, user_id, source, payload)
        
        if not event_model:
            return {
                "success": False,
                "error": "Invalid event structure",
                "event_id": None
            }
        
        # Step 2: Save to database (REQUIRED)
        saved = self._save_event(db, event_model)
        
        if not saved:
            return {
                "success": False,
                "error": "Database persistence failed",
                "event_id": event_model.event_id
            }
        
        # Step 3: Dispatch to n8n (OPTIONAL - failure doesn't fail operation)
        # Get the saved database event for dispatch
        db_event = db.query(Event).filter(
            Event.id == uuid.UUID(event_model.event_id)
        ).first()
        
        dispatched = False
        if db_event:
            dispatched = self._dispatch_to_n8n(db_event)
        
        # Return success even if webhook fails
        return {
            "success": True,
            "event_id": event_model.event_id,
            "dispatched": dispatched
        }

    def _create_event(
        self,
        event_type: str,
        user_id: str,
        source: Literal["logging_service", "chat_service"],
        payload: Dict[str, Any]
    ) -> Optional[EventModel]:
        """
        Create a structured event object with validation.
        
        Args:
            event_type: Type of event
            user_id: UUID string of the user
            source: Service that generated the event
            payload: Event-specific data
            
        Returns:
            EventModel object if valid, None if validation fails
        """
        try:
            event = EventModel(
                event_type=event_type,
                user_id=user_id,
                source=source,
                payload=payload
            )
            logger.info(f"Event created: {event.event_id} - {event.event_type}")
            return event
            
        except Exception as e:
            logger.error(f"Event creation failed: {str(e)}")
            return None

    def _save_event(self, db: Session, event_model: EventModel) -> bool:
        """
        Persist event to database.
        
        Args:
            db: Database session
            event_model: EventModel object to persist
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create database record
            event_record = Event(
                id=uuid.UUID(event_model.event_id),
                user_id=uuid.UUID(event_model.user_id),
                event_type=event_model.event_type,
                payload=event_model.payload,
                created_at=datetime.fromisoformat(event_model.timestamp)
            )
            
            db.add(event_record)
            db.commit()
            
            logger.info(f"Event persisted: {event_model.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Event persistence failed: {event_model.event_id} - {str(e)}")
            db.rollback()
            return False

    def _dispatch_to_n8n(self, event: Event) -> bool:
        """
        Dispatch event to n8n webhook.
        
        This sends the event to external automation systems.
        Failures here DO NOT block the main request.
        
        Args:
            event: Database Event object to dispatch
            
        Returns:
            True if dispatched successfully, False otherwise
        """
        try:
            # Import n8n adapter
            from services.integrations.n8n_adapter import send_event_to_n8n
            
            # Convert database event to dict for webhook
            event_dict = {
                "event_id": str(event.id),
                "event_type": event.event_type,
                "user_id": str(event.user_id),
                "payload": event.payload,
                "timestamp": event.created_at.isoformat()
            }
            
            # Attempt webhook delivery
            success = send_event_to_n8n(event_dict)
            
            if success:
                logger.info(f"Event dispatched to n8n: {event.id}")
            else:
                logger.warning(f"Event dispatch to n8n failed: {event.id}")
                
            return success
            
        except Exception as e:
            # Webhook failure should not crash the system
            logger.error(f"Event dispatch error: {event.id} - {str(e)}")
            return False

    # v0.2 METHODS (keep for backward compatibility)
    def get_user_events(
        self,
        db: Session,
        user_id: uuid.UUID,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """
        Get recent events for a user.
        
        Args:
            db: Database session
            user_id: User UUID
            event_type: Optional filter by event type
            limit: Maximum number of events to return
        
        Returns:
            List of Event objects, newest first
        """
        query = db.query(Event).filter(Event.user_id == user_id)
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        events = query.order_by(
            Event.created_at.desc()
        ).limit(limit).all()
        
        return events

    def get_event_by_id(
        self,
        db: Session,
        event_id: uuid.UUID
    ) -> Optional[Event]:
        """
        Get specific event by ID.
        
        Args:
            db: Database session
            event_id: Event UUID
        
        Returns:
            Event object if found, None otherwise
        """
        return db.query(Event).filter(Event.id == event_id).first()
# ── Module-level convenience functions for v0.4 services ─────────────────────
# weekly_summary_service and drift_service import these directly.

_bus = EventBus()

def emit_event(
    event_type: str,
    user_id: str,
    source: str,
    payload: Dict[str, Any],
    db: Session
) -> Dict[str, Any]:
    """Standalone wrapper around EventBus.emit_event for easy importing."""
    # Allow weekly_summary_service as a valid source
    allowed_sources = ["logging_service", "chat_service", "weekly_summary_service"]
    if source not in allowed_sources:
        source = "logging_service"  # safe fallback
    return _bus.emit_event(
        db=db,
        event_type=event_type,
        user_id=user_id,
        source=source,
        payload=payload
    )