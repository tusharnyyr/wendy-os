"""
Intent Router for Wendy v0.1
Rule-based message routing (no AI classification).
"""
from typing import Dict, Any


class IntentRouter:
    """Rule-based intent detection and routing."""

    @staticmethod
    def detect_intent(message: str) -> Dict[str, Any]:
        """
        Detect user intent from message using rule-based matching.
        
        Args:
            message: User's message text
        
        Returns:
            Dictionary with:
                - intent: str ("log" or "chat")
                - payload: str (message content after stripping prefix)
        """
        # Normalize message (strip whitespace)
        normalized_message = message.strip()
        
        # Check if message starts with "Log:" (case-insensitive)
        if normalized_message.lower().startswith("log:"):
            # Extract content after "Log:"
            payload = normalized_message[4:].strip()
            
            return {
                "intent": "log",
                "payload": payload
            }
        
        # Default: treat as chat
        return {
            "intent": "chat",
            "payload": normalized_message
        }

    @staticmethod
    def is_log_command(message: str) -> bool:
        """
        Quick check if message is a log command.
        
        Args:
            message: User's message text
        
        Returns:
            True if message starts with "Log:", False otherwise
        """
        return message.strip().lower().startswith("log:")

    @staticmethod
    def extract_log_content(message: str) -> str:
        """
        Extract content from log command.
        
        Args:
            message: User's message (should start with "Log:")
        
        Returns:
            Content after "Log:" prefix
        """
        normalized_message = message.strip()
        
        if normalized_message.lower().startswith("log:"):
            return normalized_message[4:].strip()
        
        return normalized_message