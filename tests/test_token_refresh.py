"""
Tests for token refresh (POST /api/auth/refresh) and 401 retry behavior.
Spec: docs/specs/2026-01-29-token-refresh.md
"""
import pytest
from unittest.mock import patch, MagicMock

from a700cli.core.session import SessionManager


def test_session_manager_stores_and_loads_cookies(tmp_path):
    """SessionManager persists cookies so refresh can use them."""
    with patch("a700cli.core.session.get_state_dir", return_value=tmp_path / ".agent700"):
        sm = SessionManager()
        sm.save_session({
            "access_token": "old_token",
            "email": "u@example.com",
            "cookies": {"refreshToken": "rt_abc"},
        })
        loaded = sm.load_session()
        assert loaded.get("cookies") == {"refreshToken": "rt_abc"}
        assert loaded.get("access_token") == "old_token"


def test_refresh_returns_new_token_when_api_succeeds():
    """When POST /api/auth/refresh returns 200, refresh helper returns new access token."""
    from a700cli.__main__ import refresh_access_token

    session_data = {
        "access_token": "old_token",
        "email": "u@example.com",
        "cookies": {"refreshToken": "rt_abc"},
    }
    with patch("a700cli.__main__.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"accessToken": "new_token", "expiresIn": 3600, "message": "OK"},
        )
        with patch.object(SessionManager, "load_session", return_value=session_data):
            with patch.object(SessionManager, "save_session") as mock_save:
                sm = SessionManager()
                result = refresh_access_token("https://api.agent700.ai", sm)
                assert result == "new_token"
                mock_save.assert_called_once()
                call_args = mock_save.call_args[0][0]
                assert call_args.get("access_token") == "new_token"


def test_refresh_returns_none_when_no_cookies():
    """When session has no cookies, refresh returns None."""
    from a700cli.__main__ import refresh_access_token

    with patch.object(SessionManager, "load_session", return_value={"access_token": "t", "email": "e@e.com"}):
        sm = SessionManager()
        result = refresh_access_token("https://api.agent700.ai", sm)
        assert result is None


def test_refresh_returns_none_when_api_returns_401():
    """When POST /api/auth/refresh returns 401, refresh returns None."""
    from a700cli.__main__ import refresh_access_token

    session_data = {"access_token": "old", "email": "u@e.com", "cookies": {"refreshToken": "rt"}}
    with patch("a700cli.__main__.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=401, json=lambda: {"error": "Unauthorized"})
        with patch.object(SessionManager, "load_session", return_value=session_data):
            sm = SessionManager()
            result = refresh_access_token("https://api.agent700.ai", sm)
            assert result is None


def test_get_agent_config_retries_after_refresh_on_401():
    """When get_agent_config gets 401, refresh is attempted and request is retried with new token."""
    from a700cli.__main__ import get_agent_config

    console = MagicMock()
    session_manager = MagicMock()
    # First call 401, then 200 after refresh
    with patch("a700cli.__main__.requests.get") as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=401),
            MagicMock(
                status_code=200,
                json=lambda: {
                    "revisions": [{
                        "id": 1, "name": "Test", "enableMcp": False, "mcpServerNames": [],
                        "model": "gpt-4o", "masterPrompt": "", "temperature": 0.7, "maxTokens": 4000,
                        "imageDimensions": "1024x1024", "topP": 1.0, "scrubPii": False, "piiThreshold": 0.5,
                    }]
                },
            ),
        ]
        with patch("a700cli.__main__.refresh_access_token") as mock_refresh:
            mock_refresh.return_value = "new_token"
            result = get_agent_config(
                "old_token", "agent-uuid", "https://api.agent700.ai", console,
                session_manager=session_manager,
            )
            assert mock_refresh.call_count == 1
            assert result.get("agentName") == "Test"
            # Second request should use new token
            assert mock_get.call_count == 2
            second_call_headers = mock_get.call_args_list[1][1].get("headers", {})
            assert second_call_headers.get("Authorization") == "Bearer new_token"
