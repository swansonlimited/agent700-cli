"""
Shared test utilities, mocks, and fixtures for a700cli tests.
"""
import json
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock, patch
import requests
from dataclasses import dataclass


@dataclass
class MockResponse:
    """Mock HTTP response for testing."""
    status_code: int
    json_data: Dict[str, Any] = None
    text: str = ""
    
    def json(self):
        return self.json_data or {}
    
    @property
    def content(self):
        return json.dumps(self.json_data or {}).encode()


class MockConsole:
    """Mock console for testing (replaces Rich Console)."""
    def __init__(self):
        self.output = []
        self.quiet = False
    
    def print(self, *args, **kwargs):
        if not self.quiet:
            self.output.append(" ".join(str(arg) for arg in args))
    
    def print_panel(self, content, title="", style=""):
        if not self.quiet:
            self.output.append(f"[{title}] {content}")


class MockSessionManager:
    """Mock session manager for testing."""
    def __init__(self):
        self.session_data = {}
        self.session_file = Path(".test_session.dat")
    
    def load_session(self) -> Dict[str, Any]:
        return self.session_data
    
    def save_session(self, data: Dict[str, Any]):
        self.session_data.update(data)


class MockConversationManager:
    """Mock conversation manager for testing."""
    def __init__(self):
        self.conversation_history = []
        self.conversation_file = Path(".test_conversation.json")
    
    def load_conversation(self) -> List[Dict[str, Any]]:
        return self.conversation_history
    
    def save_conversation(self):
        pass
    
    def add_user_message(self, message: str):
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": "2025-01-27T00:00:00"
        })
    
    def add_agent_message(self, message: str):
        self.conversation_history.append({
            "role": "agent",
            "content": message,
            "timestamp": "2025-01-27T00:00:00"
        })

    def clear(self):
        self.conversation_history = []

    def get_conversation_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.conversation_history[-limit:]

    def to_api_messages(self, limit: int = 10) -> List[Dict[str, str]]:
        api_messages = []
        for message in self.get_conversation_context(limit=limit):
            role = "assistant" if message.get("role") == "agent" else message.get("role")
            api_messages.append({"role": role, "content": message.get("content", "")})
        return api_messages


def create_mock_auth_response(access_token: str = "test_token_123") -> MockResponse:
    """Create a mock successful authentication response."""
    return MockResponse(
        status_code=200,
        json_data={
            "accessToken": access_token,
            "email": "test@example.com",
            "defaultOrganization": {"name": "Test Org"}
        }
    )


def create_mock_agent_config_response() -> MockResponse:
    """Create a mock agent configuration response."""
    return MockResponse(
        status_code=200,
        json_data={
            "revisions": [{
                "id": 1,
                "name": "Test Agent",
                "enableMcp": False,
                "mcpServerNames": [],
                "model": "gpt-4o",
                "masterPrompt": "",
                "temperature": 0.7,
                "maxTokens": 4000,
                "imageDimensions": "1024x1024",
                "topP": 1.0,
                "scrubPii": False,
                "piiThreshold": 0.5
            }]
        }
    )


def create_mock_chat_response(content: str = "Test response", citations: List[str] = None) -> MockResponse:
    """Create a mock chat API response."""
    return MockResponse(
        status_code=200,
        json_data={
            "content": content,
            "citations": citations or [],
            "response": content,
            "message": content
        }
    )


def create_mock_agents_response() -> MockResponse:
    """Create a mock agents list response."""
    return MockResponse(
        status_code=200,
        json_data={
            "agents": [
                {
                    "uuid": "agent-123",
                    "name": "Test Agent 1"
                },
                {
                    "uuid": "agent-456",
                    "name": "Test Agent 2"
                }
            ]
        }
    )


def mock_requests_post_success(url: str, **kwargs):
    """Mock successful POST request."""
    if "/auth/login" in url:
        return create_mock_auth_response()
    elif "/chat" in url:
        return create_mock_chat_response()
    return MockResponse(status_code=200, json_data={})


def mock_requests_get_success(url: str, **kwargs):
    """Mock successful GET request."""
    if "/agents/" in url and "/agents" != url:
        # Single agent request
        return create_mock_agent_config_response()
    elif "/agents" in url:
        # Agents list request
        return create_mock_agents_response()
    return MockResponse(status_code=200, json_data={})


def create_test_input_file(content: str, tmp_path: Path) -> Path:
    """Create a temporary input file for testing."""
    input_file = tmp_path / "test_input.txt"
    input_file.write_text(content)
    return input_file


def create_test_output_file(tmp_path: Path) -> Path:
    """Create a temporary output file for testing."""
    return tmp_path / "test_output.txt"


def read_test_output_file(output_file: Path) -> str:
    """Read content from test output file."""
    return output_file.read_text()


def mock_websocket_client():
    """Create a mock WebSocket client."""
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.response_complete = False
    mock_client.full_response = ""
    mock_client.citations = []
    mock_client.mcp_results = []
    mock_client.error_occurred = False
    return mock_client
