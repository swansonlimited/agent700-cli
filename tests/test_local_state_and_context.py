from unittest.mock import MagicMock, patch

from a700cli.__main__ import send_message_http
from a700cli.core.conversation import ConversationManager
from a700cli.core.session import SessionManager
from tests.test_utils import MockConversationManager


def test_session_manager_uses_user_state_dir(tmp_path):
    state_dir = tmp_path / ".agent700"
    with patch("a700cli.core.session.get_state_dir", return_value=state_dir):
        sm = SessionManager()
        sm.save_session({"access_token": "token", "cookies": {"refreshToken": "rt"}})

        assert sm.session_file == state_dir / "session.dat"
        assert sm.load_session()["access_token"] == "token"


def test_conversation_manager_maps_recent_history_for_api(tmp_path):
    state_dir = tmp_path / ".agent700"
    with patch("a700cli.core.conversation.get_state_dir", return_value=state_dir):
        cm = ConversationManager()
        cm.add_user_message("first")
        cm.add_agent_message("second")

        assert cm.conversation_file == state_dir / "conversations" / "default.json"
        assert cm.to_api_messages() == [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]


def test_send_message_http_includes_recent_conversation_context():
    conversation_manager = MockConversationManager()
    conversation_manager.add_user_message("earlier question")
    conversation_manager.add_agent_message("earlier answer")

    with patch("a700cli.__main__.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"content": "fresh answer", "citations": []},
        )

        response = send_message_http(
            "token",
            "agent-uuid",
            "new question",
            "https://api.agent700.ai",
            {},
            conversation_manager,
            console=MagicMock(),
            silent=True,
        )

        assert response.content == "fresh answer"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["messages"] == [
            {"role": "user", "content": "earlier question"},
            {"role": "assistant", "content": "earlier answer"},
            {"role": "user", "content": "new question"},
        ]
