# services/suggestion_engine.py
# New in Wendy OS v0.4
# Hybrid: rules detect behavioral pattern → AI refines phrasing

import os
from groq import Groq
from typing import Optional


# Patterns the rule engine can detect
PATTERN_TYPES = [
    "category_imbalance",
    "growth_reinforcement",
    "decline_warning",
    "low_consistency",
    "streak_break",
]


def detect_pattern(structured_summary: dict) -> Optional[dict]:
    """
    Rule-based pattern detection.
    Returns a structured suggestion intent or None.
    """
    breakdown: dict = structured_summary.get("category_breakdown", {})
    active_days: int = structured_summary.get("active_days", 0)
    streak: int = structured_summary.get("streak_days", 0)
    total_minutes: int = structured_summary.get("total_minutes", 0)

    # No activity at all
    if total_minutes == 0:
        return {
            "type": "low_consistency",
            "message_intent": "User logged no activity this week.",
            "recommended_adjustment_minutes": 30,
        }

    # Low consistency — fewer than 3 active days
    if active_days < 3:
        return {
            "type": "low_consistency",
            "active_days": active_days,
            "message_intent": f"Only {active_days} active days logged this week.",
            "recommended_adjustment_minutes": 30,
        }

    # Streak break — had streak but it's now 0
    if streak == 0 and active_days > 0:
        return {
            "type": "streak_break",
            "message_intent": "User broke their streak this week.",
            "recommended_adjustment_minutes": 15,
        }

    # Category imbalance — one category dominates (>70% of time)
    if breakdown:
        dominant_category = max(breakdown, key=breakdown.get)
        dominant_pct = breakdown[dominant_category] / total_minutes
        if dominant_pct > 0.70 and len(breakdown) > 1:
            return {
                "type": "category_imbalance",
                "category": dominant_category,
                "dominance_pct": round(dominant_pct * 100, 1),
                "message_intent": f"{dominant_category} dominated at {round(dominant_pct*100)}% of logged time.",
                "recommended_adjustment_minutes": 45,
            }

    # Growth reinforcement — all looks healthy
    return {
        "type": "growth_reinforcement",
        "active_days": active_days,
        "streak": streak,
        "message_intent": "User had a consistent and balanced week.",
        "recommended_adjustment_minutes": 0,
    }


def refine_suggestion_with_ai(suggestion_intent: dict, structured_summary: dict) -> str:
    """
    Use Groq AI to turn the raw suggestion intent into a friendly, human message.
    Falls back to raw intent message if AI call fails.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return suggestion_intent.get("message_intent", "Keep going!")

    try:
        client = Groq(api_key=api_key)
        prompt = (
            f"You are Wendy, a personal productivity assistant. "
            f"Based on this weekly data: {structured_summary} "
            f"and this behavioral pattern: {suggestion_intent}, "
            f"write ONE concise, motivating suggestion (2-3 sentences max). "
            f"Be warm and specific. Do not use bullet points."
        )
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fail gracefully — return raw intent
        print(f"[suggestion_engine] AI refinement failed: {e}")
        return suggestion_intent.get("message_intent", "Keep going!")


def generate_suggestion(structured_summary: dict) -> dict:
    """
    Full pipeline: detect pattern → refine with AI → return suggestion object.
    """
    intent = detect_pattern(structured_summary)
    if not intent:
        return {"type": "none", "text": "Great week! Keep it up."}

    refined_text = refine_suggestion_with_ai(intent, structured_summary)
    return {
        "type": intent["type"],
        "text": refined_text,
        "raw_intent": intent,
    }