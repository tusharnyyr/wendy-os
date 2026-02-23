"""
n8n Adapter for Wendy v0.3
Handles webhook communication with n8n automation platform.

Responsibilities:
- Send events to n8n webhook
- Handle webhook failures gracefully
- Read webhook URL from environment
- Operate safely when webhook not configured
"""

import os
import logging
import requests
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


def send_event_to_n8n(event_dict: Dict[str, Any]) -> bool:
    """
    Send event to n8n webhook.
    
    This function sends structured events to n8n for external automation.
    If the webhook URL is not configured, it skips silently.
    
    Args:
        event_dict: Event data containing:
            - event_id: UUID string
            - event_type: Type of event
            - user_id: User UUID string
            - payload: Event-specific data
            - timestamp: ISO8601 timestamp
            
    Returns:
        True if webhook sent successfully, False otherwise
    """
    # Read webhook URL from environment
    n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
    
    # If webhook not configured, skip gracefully
    if not n8n_webhook_url:
        logger.debug("N8N_WEBHOOK_URL not configured, skipping webhook")
        return False
    
    # If webhook URL is empty string, skip gracefully
    if not n8n_webhook_url.strip():
        logger.debug("N8N_WEBHOOK_URL is empty, skipping webhook")
        return False
    
    try:
        # Send POST request to n8n webhook
        response = requests.post(
            n8n_webhook_url,
            json=event_dict,
            timeout=5  # 5 second timeout
        )
        
        # Check if request was successful (2xx status codes)
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Event sent to n8n successfully: {event_dict.get('event_id')}")
            return True
        else:
            logger.warning(
                f"n8n webhook returned status {response.status_code} "
                f"for event {event_dict.get('event_id')}"
            )
            return False
    
    except requests.exceptions.Timeout:
        logger.error(f"n8n webhook timeout for event {event_dict.get('event_id')}")
        return False
    
    except requests.exceptions.ConnectionError:
        logger.error(f"n8n webhook connection failed for event {event_dict.get('event_id')}")
        return False
    
    except requests.exceptions.RequestException as e:
        logger.error(f"n8n webhook request failed: {str(e)}")
        return False
    
    except Exception as e:
        logger.error(f"Unexpected error sending to n8n: {str(e)}")
        return False


def test_n8n_connection() -> Dict[str, Any]:
    """
    Test connection to n8n webhook.
    
    Useful for debugging and health checks.
    
    Returns:
        Dict with:
            - configured: bool (is webhook URL set?)
            - reachable: bool (can we connect?)
            - url: str (webhook URL, if configured)
    """
    n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
    
    if not n8n_webhook_url or not n8n_webhook_url.strip():
        return {
            "configured": False,
            "reachable": False,
            "url": None
        }
    
    try:
        # Send a test ping
        test_payload = {
            "event_type": "test_connection",
            "message": "Wendy OS connection test"
        }
        
        response = requests.post(
            n8n_webhook_url,
            json=test_payload,
            timeout=5
        )
        
        return {
            "configured": True,
            "reachable": response.status_code >= 200 and response.status_code < 300,
            "url": n8n_webhook_url,
            "status_code": response.status_code
        }
    
    except Exception as e:
        return {
            "configured": True,
            "reachable": False,
            "url": n8n_webhook_url,
            "error": str(e)
        }