"""
Session management for authentication persistence.
"""
from typing import Dict, Any
from pathlib import Path
import pickle


def get_state_dir() -> Path:
    """Return the per-user state directory for local CLI data."""
    return Path.home() / ".agent700"


class SessionManager:
    """Manages session persistence for authentication."""
    
    def __init__(self) -> None:
        self.session_file = get_state_dir() / "session.dat"
        self.legacy_session_file = Path(".agent700_session.dat")
        self.session_data = self.load_session()
    
    def load_session(self) -> Dict[str, Any]:
        """Load session data from file."""
        for candidate in (self.session_file, self.legacy_session_file):
            if not candidate.exists():
                continue
            try:
                with open(candidate, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load session: {e}")
        return {}
    
    def save_session(self, data: Dict[str, Any]) -> None:
        """Save session data to file."""
        self.session_data.update(data)
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, 'wb') as f:
                pickle.dump(self.session_data, f)
        except Exception as e:
            print(f"Warning: Could not save session: {e}")
