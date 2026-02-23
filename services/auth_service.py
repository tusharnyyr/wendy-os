"""
Authentication Service for Wendy v0.1
Handles user resolution from WhatsApp phone numbers and API tokens.
"""
from sqlalchemy.orm import Session
from typing import Optional
from database.models import User


class AuthService:
    """Service for user authentication and resolution."""

    @staticmethod
    def resolve_user_from_phone(db: Session, phone_number: str) -> Optional[User]:
        """
        Resolve user by WhatsApp phone number.
        
        Args:
            db: Database session
            phone_number: WhatsApp phone number (e.g., "+919876543210")
        
        Returns:
            User object if found, None otherwise
        """
        # Normalize phone number (remove spaces, dashes)
        normalized_phone = phone_number.replace(" ", "").replace("-", "")
        
        user = db.query(User).filter(
            User.whatsapp_number == normalized_phone
        ).first()
        
        return user

    @staticmethod
    def resolve_user_from_token(db: Session, api_token: str) -> Optional[User]:
        """
        Resolve user by API token.
        
        Args:
            db: Database session
            api_token: API authentication token
        
        Returns:
            User object if found, None otherwise
        """
        user = db.query(User).filter(
            User.api_token == api_token
        ).first()
        
        return user

    @staticmethod
    def create_user(
        db: Session,
        name: str,
        email: str,
        whatsapp_number: Optional[str] = None,
        api_token: Optional[str] = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            db: Database session
            name: User's name
            email: User's email
            whatsapp_number: Optional WhatsApp number
            api_token: Optional API token
        
        Returns:
            Created User object
        """
        user = User(
            name=name,
            email=email,
            whatsapp_number=whatsapp_number,
            api_token=api_token
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            db: Database session
            user_id: User's UUID
        
        Returns:
            User object if found, None otherwise
        """
        user = db.query(User).filter(User.id == user_id).first()
        return user

# Addition to auth_service.py
# v0.4: Telegram user resolution

def get_user_by_telegram_id(telegram_user_id: str, db: Session):
    """Resolve a Wendy user from their Telegram user ID."""
    return (
        db.query(User)
        .filter(User.telegram_user_id == telegram_user_id)
        .first()
    )