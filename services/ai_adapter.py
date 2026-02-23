"""
AI Adapter for Wendy v0.2
Handles AI-powered parsing of activity logs using Groq (FREE).
Now includes chat conversation support.
"""
from typing import List, Dict
import os
import json
from typing import Dict, Any
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIAdapter:
    """Adapter for AI-powered text parsing using Groq."""

    # Allowed activity categories
    ALLOWED_CATEGORIES = ["Learning", "Work", "Fitness", "Personal", "Project"]

    def __init__(self):
        """Initialize Groq client."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"  # Free, fast, and accurate

    def parse_log_to_json(self, log_text: str) -> Dict[str, Any]:
        """
        Parse natural language log entry into structured JSON.
        
        Args:
            log_text: Natural language description of activity
                     e.g., "Studied Python for 2 hours in the morning"
        
        Returns:
            Dictionary with:
                - success: bool
                - data: dict (if success=True)
                    - activity_name: str
                    - category: str (one of ALLOWED_CATEGORIES)
                    - duration_minutes: int
                    - notes: str (optional)
                - error: str (if success=False)
        """
        try:
            # Create system prompt
            system_prompt = self._build_system_prompt()
            
            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": log_text
                    }
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=200
            )
            
            # Extract response text
            response_text = chat_completion.choices[0].message.content.strip()
            
            # Parse JSON response
            parsed_data = self._parse_json_response(response_text)
            
            # Validate parsed data
            validation_result = self._validate_parsed_data(parsed_data)
            
            if validation_result["valid"]:
                return {
                    "success": True,
                    "data": parsed_data
                }
            else:
                return {
                    "success": False,
                    "error": validation_result["error"]
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"AI parsing failed: {str(e)}"
            }

    def _build_system_prompt(self) -> str:
        """Build system prompt for Groq."""
        return f"""You are a JSON parser for activity logs. Convert natural language into structured JSON.

RULES:
1. Return ONLY valid JSON, no other text
2. Required fields: activity_name, category, duration_minutes, notes
3. Categories MUST be one of: {', '.join(self.ALLOWED_CATEGORIES)}
4. Duration conversion:
   - "2h" or "2 hours" → 120
   - "45m" or "45 minutes" → 45
   - "1.5h" → 90
   - If no duration specified → 30 (default)
5. Extract activity name (clean, concise)
6. Put extra details in notes field

OUTPUT FORMAT:
{{
  "activity_name": "Brief activity description",
  "category": "One of the allowed categories",
  "duration_minutes": 30,
  "notes": "Additional context or empty string"
}}

EXAMPLES:
Input: "Studied Python for 2 hours"
Output: {{"activity_name": "Studied Python", "category": "Learning", "duration_minutes": 120, "notes": ""}}

Input: "Morning run 5km"
Output: {{"activity_name": "Morning run", "category": "Fitness", "duration_minutes": 30, "notes": "5km"}}

Input: "Client meeting about Q3 project for 1.5h"
Output: {{"activity_name": "Client meeting", "category": "Work", "duration_minutes": 90, "notes": "Q3 project"}}"""

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from AI response, handling potential formatting issues.
        """
        # Remove markdown code blocks if present
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        
        cleaned_text = cleaned_text.strip()
        
        # Parse JSON
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

    def _validate_parsed_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsed data structure and values."""
        # Check required fields
        required_fields = ["activity_name", "category", "duration_minutes", "notes"]
        for field in required_fields:
            if field not in data:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}"
                }
        
        # Validate category
        if data["category"] not in self.ALLOWED_CATEGORIES:
            return {
                "valid": False,
                "error": f"Invalid category '{data['category']}'. Must be one of: {', '.join(self.ALLOWED_CATEGORIES)}"
            }
        
        # Validate duration_minutes is positive integer
        try:
            duration = int(data["duration_minutes"])
            if duration <= 0:
                return {
                    "valid": False,
                    "error": "duration_minutes must be positive"
                }
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": "duration_minutes must be an integer"
            }
        
        # Validate activity_name is non-empty
        if not data["activity_name"] or not data["activity_name"].strip():
            return {
                "valid": False,
                "error": "activity_name cannot be empty"
            }
        
        return {"valid": True}

    # ========================================
    # NEW METHOD FOR v0.2 - Chat Support
    # ========================================
    def generate_chat_response(
        self, 
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        current_message: str
    ) -> str:
        """
        Generate conversational response using Groq.
        
        Args:
            system_prompt: System instructions (Wendy personality + context)
            conversation_history: List of {role, content} dicts
            current_message: Current user message
            
        Returns:
            Assistant's response text
        """
        try:
            # Build messages array
            messages = []
            
            # Add system message
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": current_message
            })
            
            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=1024
            )
            
            # Extract text from response
            return chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"AI generation error: {str(e)}")
            raise