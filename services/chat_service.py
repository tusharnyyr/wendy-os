"""
Wendy OS v0.3 - Chat Service
Handles conversational interactions with context from logs and history.

v0.3 Changes:
- Emits structured "chat_message_created" events via EventBus
- Integrated with new event_bus.emit_event() method
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

# Import from correct paths for your project structure
from database.models import Conversation, ActivityLog  # Database models
from services.ai_adapter import AIAdapter  # AI interface
from services.event_bus import EventBus  # v0.3: Event bus


class ChatService:
    """
    Chat Service for Wendy OS
    
    Responsibilities:
    - Fetch recent conversations
    - Compute log summary from last 7 days
    - Build structured context
    - Generate AI response
    - Store conversation
    - Emit chat events (v0.3 NEW)
    """
    
    def __init__(self, db: Session, ai_adapter: AIAdapter = None):
        self.db = db
        # Initialize AI adapter if not provided
        if ai_adapter is None:
            self.ai = AIAdapter()
        else:
            self.ai = ai_adapter
        self.event_bus = EventBus()  # v0.3: Added event bus
        self.conversation_limit = 15
        self.log_summary_days = 7
    
    def handle_chat(self, user_id: str, message: str) -> str:
        """
        Main chat handler
        
        Args:
            user_id: Authenticated user identifier
            message: User's message text
            
        Returns:
            Assistant's response text
            
        Raises:
            Exception: On critical failures (DB, AI)
        """
        try:
            # Step 1: Fetch conversation history
            conversations = self._fetch_recent_conversations(user_id)
            
            # Step 2: Fetch log summary
            log_summary = self._fetch_log_summary(user_id)
            
            # Step 3: Build context
            context = self._build_context(log_summary, conversations, message)
            
            # Step 4: Generate AI response
            response = self._generate_response(context)
            
            # Step 5: Store conversation
            conversation_stored = self._store_conversation(user_id, message, response)
            
            # Step 6: v0.3 NEW - Emit "chat_message_created" event
            if conversation_stored:
                event_result = self.event_bus.emit_event(
                    db=self.db,
                    event_type="chat_message_created",
                    user_id=user_id,
                    source="chat_service",
                    payload={
                        "user_message": message,
                        "assistant_message": response,
                        "message_length": len(message),
                        "response_length": len(response),
                        "has_log_context": log_summary.get("has_data", False),
                        "conversation_count": len(conversations) // 2  # Divide by 2 (user + assistant pairs)
                    }
                )
                
                # Log event emission result (for debugging)
                if not event_result["success"]:
                    print(f"Warning: Event emission failed: {event_result.get('error')}")
            
            return response
            
        except Exception as e:
            # Log error (assuming logging is configured)
            print(f"Chat service error for user {user_id}: {str(e)}")
            return "Wendy is temporarily unavailable. Please try again."
    
    def _fetch_recent_conversations(self, user_id: str) -> List[Dict]:
        """
        Fetch last N conversations for context
        
        Args:
            user_id: User identifier
            
        Returns:
            List of conversation dicts with role and content
        """
        try:
            conversations = (
                self.db.query(Conversation)
                .filter(Conversation.user_id == user_id)
                .order_by(Conversation.created_at.desc())
                .limit(self.conversation_limit)
                .all()
            )
            
            # Reverse to get chronological order
            conversations = list(reversed(conversations))
            
            result = []
            for conv in conversations:
                result.append({
                    "role": "user",
                    "content": conv.user_message
                })
                result.append({
                    "role": "assistant",
                    "content": conv.assistant_message
                })
            
            return result
            
        except Exception as e:
            print(f"Error fetching conversations: {str(e)}")
            return []
    
    def _fetch_log_summary(self, user_id: str) -> Dict:
        """
        Compute activity log summary for last 7 days
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with summary statistics
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=self.log_summary_days)
            
            # Query logs in date range
            logs = (
                self.db.query(ActivityLog)
                .filter(
                    and_(
                        ActivityLog.user_id == user_id,
                        ActivityLog.created_at >= start_date
                    )
                )
                .all()
            )
            
            if not logs:
                return {
                    "has_data": False,
                    "message": "No recent logs available."
                }
            
            # Compute statistics
            category_minutes = {}
            for log in logs:
                # Handle category being an Enum or string
                category = log.category.value if hasattr(log.category, 'value') else str(log.category)
                duration = log.duration_minutes or 0
                
                if category in category_minutes:
                    category_minutes[category] += duration
                else:
                    category_minutes[category] = duration
            
            # Find most active category
            most_active = max(category_minutes.items(), key=lambda x: x[1]) if category_minutes else (None, 0)
            
            return {
                "has_data": True,
                "total_logs": len(logs),
                "category_minutes": category_minutes,
                "most_active_category": most_active[0],
                "most_active_minutes": most_active[1],
                "period_days": self.log_summary_days
            }
            
        except Exception as e:
            print(f"Error fetching log summary: {str(e)}")
            return {
                "has_data": False,
                "message": "No recent logs available."
            }
    
    def _build_context(
        self, 
        log_summary: Dict, 
        conversations: List[Dict], 
        current_message: str
    ) -> Dict:
        """
        Build structured context for AI
        
        Args:
            log_summary: Activity log statistics
            conversations: Recent conversation history
            current_message: Current user message
            
        Returns:
            Context dictionary for AI adapter
        """
        # System prompt - Wendy's personality
        system_prompt = """You are Wendy OS, a personal AI operating system inside Project Wendy.
You have access to the user's recent structured activity logs and conversation history.
Use only available data.
Do not fabricate statistics.
Provide concise, analytical, helpful responses.

You are calm, structured, analytical, subtle, and non-judgmental.
Your tone is professional, clear, and observational - not dramatic."""
        
        # Add log summary to system prompt
        if log_summary.get("has_data"):
            system_prompt += f"\n\nUser recent activity summary (last {log_summary['period_days']} days):\n"
            
            for category, minutes in log_summary["category_minutes"].items():
                system_prompt += f"{category}: {minutes} minutes\n"
            
            system_prompt += f"Logs this week: {log_summary['total_logs']}"
        else:
            system_prompt += f"\n\n{log_summary.get('message', 'No recent logs available.')}"
        
        return {
            "system_prompt": system_prompt,
            "conversation_history": conversations,
            "current_message": current_message
        }
    
    def _generate_response(self, context: Dict) -> str:
        """
        Generate AI response using adapter
        
        Args:
            context: Structured context dictionary
            
        Returns:
            AI generated response text
            
        Raises:
            Exception: If AI call fails
        """
        try:
            response = self.ai.generate_chat_response(
                system_prompt=context["system_prompt"],
                conversation_history=context["conversation_history"],
                current_message=context["current_message"]
            )
            return response
            
        except Exception as e:
            print(f"AI generation error: {str(e)}")
            raise
    
    def _store_conversation(
        self, 
        user_id: str, 
        user_message: str, 
        assistant_message: str
    ) -> bool:
        """
        Store conversation in database
        
        Args:
            user_id: User identifier
            user_message: User's message
            assistant_message: Assistant's response
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            conversation = Conversation(
                user_id=user_id,
                user_message=user_message,
                assistant_message=assistant_message,
                created_at=datetime.utcnow()
            )
            
            self.db.add(conversation)
            self.db.commit()
            
            return True
            
        except Exception as e:
            print(f"Error storing conversation: {str(e)}")
            self.db.rollback()
            # Don't raise - conversation storage failure shouldn't break the response
            return False