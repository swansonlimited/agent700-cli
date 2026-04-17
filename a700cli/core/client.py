"""
WebSocket client for streaming responses.
Spec: docs/specs/2026-01-29-tool-execution.md
"""
import sys
import json
import re
import threading
from typing import Dict, Any, List, Optional
from typing import Any as AnyType

# WebSocket support
try:
    import socketio
    from socketio import exceptions as socketio_exceptions
    WEBSOCKET_AVAILABLE = True
except ImportError:
    socketio = None
    socketio_exceptions = None
    WEBSOCKET_AVAILABLE = False

from .models import AgentResponse
from .mcp import parse_tool_use_blocks, McpExecutor


class WebSocketClient:
    """Simplified WebSocket client for streaming responses."""
    
    def __init__(self, api_base_url: str, access_token: str, console: AnyType) -> None:
        """Initialize WebSocket client.
        
        Args:
            api_base_url: Base URL for Agent700 API
            access_token: Authentication token
            console: Console object for output
        """
        self.api_base_url = api_base_url
        self.access_token = access_token
        self.console = console
        self.sio = None
        self.response_complete = False
        self.full_response = ""
        self.tool_call_pending = False
        self.citations: List[str] = []
        self.mcp_results: List[Dict] = []
        self.error_occurred = False
        self.error_message = ""
        self.response_event = threading.Event()

        TOOL_USE_PATTERN = re.compile(r'<tool_use>[\s\S]*?</tool_use>', re.IGNORECASE)
        self._tool_use_pattern = TOOL_USE_PATTERN

        if not WEBSOCKET_AVAILABLE:
            raise ImportError("python-socketio not available")

        if not api_base_url.endswith('/api'):
            if api_base_url.endswith('/'):
                self.api_base_url = api_base_url + 'api'
            else:
                self.api_base_url = api_base_url + '/api'

        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False,
            reconnection=False
        )
        self._setup_handlers()

    @staticmethod
    def _tool_detection(finish_reason: Optional[str], content: str, tool_use_pattern: re.Pattern) -> tuple:
        """Return (tool_call_pending, response_complete) for given finish_reason and content."""
        if finish_reason == 'tool_calls':
            return (True, False)
        if (finish_reason or '').lower() in ('end_turn', 'stop'):
            if tool_use_pattern.search(content):
                return (True, False)
            return (False, True)
        return (False, False)

    def _setup_handlers(self) -> None:
        """Setup WebSocket event handlers for connection, messages, and errors."""
        @self.sio.event
        def connect():
            if not hasattr(self.console, 'quiet') or not self.console.quiet:
                self.console.print("🔌 Connected to streaming endpoint", style="green")
        
        @self.sio.event
        def disconnect():
            self.response_event.set()
        
        @self.sio.on('chat_message_response')
        def on_chat_response(data):
            content = data.get('content', '')
            finish_reason = data.get('finish_reason')
            citations = data.get('citations', [])
            
            if content:
                self.full_response += content
                sys.stdout.write(content)
                sys.stdout.flush()
            
            if citations:
                self.citations.extend(citations)
            
            tool_pending, resp_complete = self._tool_detection(
                finish_reason, self.full_response, self._tool_use_pattern
            )
            if tool_pending or resp_complete:
                self.tool_call_pending = tool_pending
                self.response_complete = resp_complete
                self.response_event.set()
        
        @self.sio.on('mcp_tool_complete_in_content')
        def on_mcp_tool_complete(data):
            try:
                result_block = data.get('result_block', [])
                if isinstance(result_block, list) and len(result_block) > 1:
                    try:
                        parsed_result = json.loads(result_block[1])
                        self.mcp_results.append(parsed_result)
                    except:
                        self.mcp_results.append({'raw': result_block})
                else:
                    self.mcp_results.append({'raw': result_block})
            except Exception:
                self.mcp_results.append({'raw': data})
        
        @self.sio.on('error')
        def on_error(data):
            self.error_occurred = True
            if isinstance(data, dict):
                self.error_message = data.get('error', str(data))
            else:
                self.error_message = str(data)
            self.response_event.set()
    
    def send_message(self, agent_uuid: str, user_message: str, agent_config: Dict[str, Any],
                    conversation_manager, timeout: int = 300) -> AgentResponse:
        """Send message via WebSocket and return response.
        
        Args:
            agent_uuid: Agent UUID
            user_message: User's message
            agent_config: Agent configuration dictionary
            conversation_manager: ConversationManager instance
            timeout: Timeout in seconds
            
        Returns:
            AgentResponse with content, citations, and MCP results
        """
        self.response_complete = False
        self.full_response = ""
        self.citations = []
        self.mcp_results = []
        self.error_occurred = False
        self.error_message = ""
        self.response_event.clear()
        
        try:
            # Connect to WebSocket
            # Import here to avoid circular dependency
            import platform
            import hashlib
            import json
            
            # Simple device fingerprint for WebSocket
            system_info = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "architecture": platform.machine(),
                "python_version": platform.python_version()
            }
            fingerprint_data = json.dumps(system_info, sort_keys=True)
            device_id = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
            
            device_headers = {
                'X-Screen-Resolution': '1920x1080',
                'X-Timezone-Offset': '0',
                'X-User-Agent': f'Agent700-CLI/2.0 ({platform.system()} {platform.release()})',
                'X-Client-Type': 'enhanced-cli',
                'X-Device-Fingerprint': device_id
            }
            stream_url = f"{self.api_base_url}/stream-chat"
            self.sio.connect(
                stream_url,
                headers=device_headers,
                transports=['websocket', 'polling'],
                wait_timeout=10
            )
        except Exception as e:
            return AgentResponse(content="", error=f"Connection failed: {e}")
        
        if not self.sio.connected:
            return AgentResponse(content="", error="Failed to connect to WebSocket endpoint")
        
        # Build payload
        messages = conversation_manager.to_api_messages()
        messages.append({"role": "user", "content": user_message})
        payload = {
            "agentId": agent_uuid,
            "Authorization": f"Bearer {self.access_token}",
            "messages": messages,
            "streamResponses": True,
            "masterPrompt": agent_config.get('masterPrompt', ''),
            "model": agent_config.get('model', 'gpt-4o'),
            "temperature": agent_config.get('temperature', 0.7),
            "maxTokens": agent_config.get('maxTokens', 4000),
        }
        
        if agent_config.get('agentRevisionId'):
            payload["revisionId"] = agent_config['agentRevisionId']
        
        if agent_config.get('enableMcp') and agent_config.get('mcpServerNames'):
            payload.update({
                "enableMcp": True,
                "mcpServerNames": agent_config['mcpServerNames']
            })
        
        max_tool_rounds = 10
        round_count = 0
        
        while round_count < max_tool_rounds:
            round_count += 1
            payload["messages"] = messages
            self.tool_call_pending = False
            self.response_complete = False
            self.response_event.clear()
            
            self.sio.emit('send_chat_message', payload)
            
            if not self.response_event.wait(timeout=timeout):
                self.error_occurred = True
                self.error_message = "Response timed out"
                break
            
            if self.error_occurred:
                break
            
            if not self.tool_call_pending:
                break
            
            tool_calls = parse_tool_use_blocks(self.full_response)
            if not tool_calls:
                self.response_complete = True
                break
            
            if not hasattr(self.console, 'quiet') or not self.console.quiet:
                self.console.print(f"\n[Tool execution: {len(tool_calls)} call(s)]", style="dim")
            
            executor = McpExecutor(
                self.api_base_url, self.access_token, agent_uuid, agent_config
            )
            messages.append({"role": "assistant", "content": self.full_response})
            for tc in tool_calls:
                result = executor.execute(tc)
                self.mcp_results.append(result)
                tool_content = json.dumps(result) if isinstance(result, dict) else str(result)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id or f"{tc.server}:{tc.tool}",
                    "content": tool_content
                })
                if not hasattr(self.console, 'quiet') or not self.console.quiet:
                    self.console.print(f"  {tc.server}/{tc.tool} -> ok", style="dim")
            
            self.full_response = ""
        
        try:
            self.sio.disconnect()
        except Exception:
            pass
        
        conversation_manager.add_user_message(user_message)
        if self.full_response:
            conversation_manager.add_agent_message(self.full_response)
        
        if self.error_occurred:
            return AgentResponse(content="", error=self.error_message)
        
        if not self.response_complete and not self.full_response:
            return AgentResponse(content="", error="Response incomplete")
        
        return AgentResponse(
            content=self.full_response,
            citations=self.citations,
            mcp_results=self.mcp_results
        )
