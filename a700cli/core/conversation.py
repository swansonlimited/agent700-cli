"""
Conversation history management.
"""
from typing import List, Dict, Any
from pathlib import Path
import json
from datetime import datetime


def get_state_dir() -> Path:
    """Return the per-user state directory for local CLI data."""
    return Path.home() / ".agent700"


class ConversationManager:
    """Manages conversation history persistence."""
    
    def __init__(self) -> None:
        self.conversation_file = get_state_dir() / "conversations" / "default.json"
        self.legacy_conversation_file = Path(".agent700_conversation.json")
        self.conversation_history = self.load_conversation()
    
    def load_conversation(self) -> List[Dict[str, Any]]:
        """Load conversation history from file."""
        for candidate in (self.conversation_file, self.legacy_conversation_file):
            if not candidate.exists():
                continue
            try:
                with open(candidate, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load conversation: {e}")
        return []
    
    def save_conversation(self) -> None:
        """Save conversation history to file."""
        try:
            self.conversation_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.conversation_file, 'w') as f:
                json.dump(self.conversation_history, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save conversation: {e}")
    
    def add_user_message(self, message: str) -> None:
        """Add a user message to conversation history."""
        self.conversation_history.append({
            "role": "user", "content": message, "timestamp": datetime.now().isoformat()
        })
        self.save_conversation()
    
    def add_agent_message(self, message: str) -> None:
        """Add an agent message to conversation history."""
        self.conversation_history.append({
            "role": "agent", "content": message, "timestamp": datetime.now().isoformat()
        })
        self.save_conversation()

    def clear(self) -> None:
        """Clear persisted conversation history."""
        self.conversation_history = []
        self.save_conversation()
    
    def get_conversation_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context."""
        return self.conversation_history[-limit:]

    def to_api_messages(self, limit: int = 10) -> List[Dict[str, str]]:
        """Convert recent history to API-ready chat messages."""
        api_messages: List[Dict[str, str]] = []
        for message in self.get_conversation_context(limit=limit):
            role = message.get("role", "")
            if role == "agent":
                role = "assistant"
            if role not in {"user", "assistant", "system", "tool"}:
                continue
            content = message.get("content")
            if not content:
                continue
            api_messages.append({"role": role, "content": content})
        return api_messages
