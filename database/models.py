"""
Database models for Wendy OS v0.4.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from database.base import Base


# Enum for activity categories
class CategoryEnum(str, enum.Enum):
    LEARNING = "Learning"
    WORK = "Work"
    FITNESS = "Fitness"
    PERSONAL = "Personal"
    PROJECT = "Project"


class User(Base):
    """User model for authentication and ownership."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    whatsapp_number = Column(String(20), unique=True, nullable=True, index=True)
    api_token = Column(String(255), unique=True, nullable=True, index=True)
    telegram_user_id = Column(String(100), unique=True, nullable=True)   # v0.4 - identifies sender
    telegram_chat_id = Column(String(100), nullable=True)                # v0.4 - used for sending alerts
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    activity_logs = relationship("ActivityLog", back_populates="user")
    events = relationship("Event", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    weekly_summaries = relationship("WeeklySummary", back_populates="user")


class ActivityLog(Base):
    """Activity log entries."""
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    activity_name = Column(String(255), nullable=False)
    category = Column(SQLEnum(CategoryEnum), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="activity_logs")


class Event(Base):
    """Event log for tracking all system actions."""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="events")


class Conversation(Base):
    """Conversation history for chat context."""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="conversations")


class WeeklySummary(Base):
    """Stores computed weekly summaries. Enables segment retrieval without recomputation."""
    __tablename__ = "weekly_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    structured_summary = Column(JSONB, nullable=False)
    narrative = Column(Text, nullable=True)
    suggestion = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="weekly_summaries")
