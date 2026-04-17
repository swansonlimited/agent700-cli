#!/usr/bin/env python3
"""
A700cli - Enhanced Agent700 CLI with Interactive Configuration
"""

import os
import sys
import json
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import requests
from dotenv import load_dotenv
import platform
import hashlib
from pathlib import Path
import pickle
from datetime import datetime
import argparse
import logging
import signal
import re

# WebSocket support
try:
    from a700cli.core.client import WEBSOCKET_AVAILABLE
except ImportError:
    WEBSOCKET_AVAILABLE = False

# Enhanced console output support
try:
    from rich.console import Console as RichConsole
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
    
    class Console(RichConsole):
        """Extended Rich Console with print_panel method."""
        def print_panel(self, text, title="", style=""):
            self.print(Panel(text, title=title, style=style))
except ImportError:
    RICH_AVAILABLE = False
    Panel = None
    
    class Console:
        def __init__(self): pass
        def print(self, *args, **kwargs): print(*args)
        def print_panel(self, text, title="", style=""): 
            print(f"\n{'='*50}")
            if title: print(f"{title}")
            print(f"{'='*50}")
            print(text)
            print(f"{'='*50}\n")

    class SilentConsole:
        """Silent console for quiet mode."""
        def __init__(self): pass
        def print(self, *args, **kwargs): pass
        def print_panel(self, *args, **kwargs): pass
    
    class Table:
        """Fallback table class when Rich is not available."""
        def __init__(self, *args, **kwargs): pass
        def add_column(self, *args, **kwargs): pass
        def add_row(self, *args, **kwargs): pass

# Import core modules
from a700cli.core import AgentResponse, SessionManager, ConversationManager, WebSocketClient

def load_environment() -> Dict[str, str]:
    """Load environment variables from .env file.
    
    Returns:
        Dictionary containing API_BASE_URL, EMAIL, PASSWORD, and AGENT_UUID
    """
    load_dotenv()
    return {
        "API_BASE_URL": os.getenv("API_BASE_URL", "https://api.agent700.ai"),
        "EMAIL": os.getenv("EMAIL"), "PASSWORD": os.getenv("PASSWORD"),
        "AGENT_UUID": os.getenv("AGENT_UUID")
    }

def get_device_fingerprint() -> str:
    """Generate a device fingerprint hash for security.
    
    Returns:
        Hexadecimal hash string (16 characters) based on system information
    """
    system_info = {
        "platform": platform.system(), "platform_release": platform.release(),
        "architecture": platform.machine(), "python_version": platform.python_version()
    }
    fingerprint_data = json.dumps(system_info, sort_keys=True)
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

def get_enhanced_device_fingerprint() -> Dict[str, str]:
    """Get enhanced device fingerprinting information for API headers.
    
    Returns:
        Dictionary with device fingerprint headers (X-Screen-Resolution, X-Timezone-Offset, etc.)
    """
    try:
        from datetime import timedelta
        now = datetime.now()
        utc_offset = now.astimezone().utcoffset() if hasattr(now, 'astimezone') else None
        timezone_offset = int(utc_offset.total_seconds() / 60) if utc_offset else 0
    except:
        timezone_offset = 0
    
    return {
        'X-Screen-Resolution': '1920x1080',
        'X-Timezone-Offset': str(timezone_offset),
        'X-User-Agent': f'Agent700-CLI/2.0 ({platform.system()} {platform.release()})',
        'X-Client-Type': 'enhanced-cli'
    }

def authenticate(email: str, password: str, api_base_url: str, console: Any) -> Optional[tuple]:
    """Authenticate with Agent700 API; return (access_token, cookies_dict) or None.
    Uses a session to capture refresh token cookie for later token refresh.
    """
    auth_url = f"{api_base_url}/api/auth/login"
    headers = {
        "Content-Type": "application/json", "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint()
    }
    payload = {"email": email, "password": password}
    
    try:
        console.print("🔐 Authenticating...", style="blue")
        session = requests.Session()
        response = session.post(auth_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("accessToken")
            if access_token:
                console.print("✅ Authentication successful", style="green")
                cookies = session.cookies.get_dict()
                return (access_token, cookies)
        console.print(f"❌ Authentication failed: {response.status_code}", style="red")
        return None
    except Exception as e:
        console.print(f"❌ Authentication error: {e}", style="red")
        return None


def refresh_access_token(api_base_url: str, session_manager: SessionManager) -> Optional[str]:
    """Attempt to refresh access token via POST /api/auth/refresh using stored cookies.
    On success updates session with new token and returns it; otherwise returns None.
    """
    session_data = session_manager.load_session()
    cookies = session_data.get("cookies") or {}
    if not cookies:
        return None
    refresh_url = f"{api_base_url}/api/auth/refresh"
    headers = {"User-Agent": "A700cli/1.0.0", "X-Device-Fingerprint": get_device_fingerprint()}
    try:
        response = requests.post(refresh_url, headers=headers, cookies=cookies, timeout=30)
        if response.status_code != 200:
            return None
        data = response.json()
        new_token = data.get("accessToken")
        if new_token:
            session_manager.save_session({"access_token": new_token})
            return new_token
        return None
    except Exception:
        return None

def validate_uuid_format(uuid_str: str) -> bool:
    """Validate UUID format (basic pattern check).
    
    Args:
        uuid_str: String to validate as UUID
        
    Returns:
        True if string matches UUID format, False otherwise
    """
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_str.lower()))

def get_agent_config(access_token: str, agent_uuid: str, api_base_url: str, console: Any, session_manager: Optional[SessionManager] = None) -> Dict[str, Any]:
    """Fetch agent configuration from API.
    
    Args:
        access_token: Authentication token
        agent_uuid: Agent UUID to fetch
        api_base_url: Base URL for API
        console: Console object for output
        session_manager: Optional session manager for token refresh on 401
        
    Returns:
        Dictionary containing agent configuration, or empty dict on error
    """
    agent_url = f"{api_base_url}/api/agents/{agent_uuid}"
    headers = {
        "Authorization": f"Bearer {access_token}", "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0", "X-Device-Fingerprint": get_device_fingerprint()
    }
    
    try:
        console.print("🔍 Fetching agent configuration...", style="blue")
        response = requests.get(agent_url, headers=headers, timeout=30)
        
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(agent_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            agent_data = response.json()
            revisions = agent_data.get('revisions', [])
            
            if revisions:
                latest_revision = max(revisions, key=lambda x: x.get('id', 0))
                config = {
                    'agentRevisionId': latest_revision.get('id'),
                    'enableMcp': latest_revision.get('enableMcp', False),
                    'mcpServerNames': latest_revision.get('mcpServerNames', []),
                    'model': latest_revision.get('model', 'gpt-4o'),
                    'agentName': latest_revision.get('name', 'Unknown Agent'),
                    'masterPrompt': latest_revision.get('masterPrompt', ''),
                    'temperature': latest_revision.get('temperature', 0.7),
                    'maxTokens': latest_revision.get('maxTokens', 4000),
                    'imageDimensions': latest_revision.get('imageDimensions', '1024x1024'),
                    'topP': latest_revision.get('topP', 1.0),
                    'scrubPii': latest_revision.get('scrubPii', False),
                    'piiThreshold': latest_revision.get('piiThreshold', 0.5)
                }
                console.print(f"✓ Agent: {config['agentName']}", style="green")
                return config
        elif response.status_code == 404:
            console.print("❌ Agent not found. Use 'a700cli --list-agents' to see available agents.", style="red")
            return {}
        elif response.status_code == 401:
            console.print("❌ Authentication failed. Please check your credentials.", style="red")
            return {}
        else:
            console.print(f"❌ Failed to get agent config: {response.status_code}", style="red")
            return {}
    except requests.exceptions.RequestException as e:
        console.print("❌ Connection failed. Check your internet connection and try again.", style="red")
        return {}
    except Exception as e:
        console.print(f"❌ Error getting agent config: {e}", style="red")
        return {}

def prompt_agent_uuid(console: Any) -> str:
    """Prompt user for agent UUID with validation.
    
    Args:
        console: Console object for output
        
    Returns:
        Valid UUID string entered by user, or empty string if cancelled
    """
    while True:
        try:
            uuid_input = input("? Enter Agent UUID: ").strip()
            
            if not uuid_input:
                console.print("❌ UUID cannot be empty. Please try again.", style="red")
                continue
            
            if not validate_uuid_format(uuid_input):
                console.print("❌ Invalid UUID format. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", style="red")
                continue
            
            return uuid_input
            
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!", style="green")
            sys.exit(0)
        except EOFError:
            console.print("\n👋 Goodbye!", style="green")
            sys.exit(0)

def list_agents(
    access_token: str,
    api_base_url: str,
    console: Any,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    output_format: str = "table",
    session_manager: Optional[SessionManager] = None,
) -> None:
    """List available agents with pagination and search.
    
    Args:
        access_token: Authentication token
        api_base_url: Base URL for API
        console: Console object for output
        page: Page number (1-indexed)
        limit: Results per page (max 100)
        search: Optional search term to filter by name (case-insensitive)
        output_format: Output format ('table' or 'json')
        session_manager: Optional session manager for token refresh on 401
    """
    agents_url = f"{api_base_url}/api/agents"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0"
    }
    
    # Enforce max limit
    limit = min(limit, 100)
    page = max(1, page)
    
    try:
        console.print("🔍 Fetching available agents...", style="blue")
        response = requests.get(agents_url, headers=headers, timeout=30)
        
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(agents_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            agents_data = response.json()
            # Handle both list response and dict with 'agents' key
            if isinstance(agents_data, list):
                all_agents = agents_data
            else:
                all_agents = agents_data.get('agents', [])
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                all_agents = [
                    agent for agent in all_agents
                    if search_lower in agent.get('name', '').lower()
                ]
            
            # Calculate pagination
            total_agents = len(all_agents)
            total_pages = (total_agents + limit - 1) // limit if total_agents > 0 else 1
            page = min(page, total_pages)
            
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_agents = all_agents[start_idx:end_idx]
            
            if output_format == "json":
                # Output as JSON array
                print(json.dumps(paginated_agents, indent=2))
                return
            
            # Table format
            if RICH_AVAILABLE:
                table = Table(title=f"Available Agents (Page {page} of {total_pages})")
                table.add_column("NAME", style="cyan", no_wrap=False)
                table.add_column("UUID", style="magenta")
                
                for agent in paginated_agents:
                    name = agent.get('name', 'Unknown')
                    uuid = agent.get('uuid', 'No UUID')
                    # Truncate UUID for display: show first 8 chars + "..."
                    uuid_display = f"{uuid[:8]}..." if len(uuid) > 12 else uuid
                    table.add_row(name, uuid_display)
                
                console.print(table)
            else:
                # Fallback plain text table
                console.print(f"\nAvailable Agents (Page {page} of {total_pages})")
                console.print("=" * 80)
                console.print(f"{'NAME':<40} {'UUID':<40}")
                console.print("=" * 80)
                
                for agent in paginated_agents:
                    name = agent.get('name', 'Unknown')
                    uuid = agent.get('uuid', 'No UUID')
                    uuid_display = f"{uuid[:8]}..." if len(uuid) > 12 else uuid
                    console.print(f"{name:<40} {uuid_display:<40}")
                
                console.print("=" * 80)
            
            if total_pages > 1:
                console.print(f"\nUse 'a700cli --list-agents --page {page + 1}' for next page" if page < total_pages else "", style="dim")
                console.print(f"Use 'a700cli --list-agents --page {page - 1}' for previous page" if page > 1 else "", style="dim")
            
            console.print("\nUse 'a700cli --list-agents --search <term>' to search by name", style="dim")
            console.print("Use 'a700cli' to activate an agent", style="dim")
            
        elif response.status_code == 401:
            console.print("❌ Authentication failed. Please check your credentials.", style="red")
        else:
            console.print(f"❌ Failed to get agents: {response.status_code}", style="red")
            
    except requests.exceptions.RequestException as e:
        console.print("❌ Connection failed. Check your internet connection and try again.", style="red")
    except Exception as e:
        console.print(f"❌ Error getting agents: {e}", style="red")


def list_orgs(
    access_token: str,
    api_base_url: str,
    console: Any,
    output_format: str = "table",
    session_manager: Optional[SessionManager] = None,
) -> None:
    """List user's organizations (id, name, role) via GET /api/organizations/my."""
    orgs_url = f"{api_base_url}/api/organizations/my"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        console.print("🔍 Fetching organizations...", style="blue")
        response = requests.get(orgs_url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(orgs_url, headers=headers, timeout=30)
        if response.status_code == 200:
            orgs = response.json()
            if not isinstance(orgs, list):
                orgs = orgs.get("organizations", []) if isinstance(orgs, dict) else []
            if output_format == "json":
                print(json.dumps(orgs, indent=2))
                return
            if RICH_AVAILABLE:
                table = Table(title="Organizations")
                table.add_column("ID", style="cyan")
                table.add_column("NAME", style="green")
                table.add_column("ROLE", style="yellow")
                for org in orgs:
                    table.add_row(
                        org.get("id", ""),
                        org.get("name", ""),
                        org.get("role", ""),
                    )
                console.print(table)
            else:
                console.print("\nOrganizations")
                console.print("=" * 60)
                console.print(f"{'ID':<38} {'NAME':<12} {'ROLE':<10}")
                console.print("=" * 60)
                for org in orgs:
                    console.print(f"{org.get('id', ''):<38} {org.get('name', ''):<12} {org.get('role', ''):<10}")
                console.print("=" * 60)
        elif response.status_code == 401:
            console.print("❌ Authentication failed. Please check your credentials.", style="red")
        else:
            console.print(f"❌ Failed to get organizations: {response.status_code}", style="red")
    except requests.exceptions.RequestException as e:
        console.print("❌ Connection failed. Check your internet connection and try again.", style="red")
    except Exception as e:
        console.print(f"❌ Error getting organizations: {e}", style="red")


def app_password_create(
    access_token: str,
    api_base_url: str,
    name: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Create app password via POST /api/auth/app-passwords. Returns True on success."""
    url = f"{api_base_url}/api/auth/app-passwords"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    payload = {"name": name}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code in (200, 201):
            data = response.json()
            token = data.get("token")
            console.print("✅ App password created. Store the token securely; it will not be shown again.", style="green")
            if token:
                console.print(f"Token: {token}", style="yellow")
            if data.get("warning"):
                console.print(data["warning"], style="dim")
            return True
        err = response.json() if response.text else {}
        console.print(f"❌ Failed to create app password: {response.status_code} {err.get('error', response.text)}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def app_password_list(
    access_token: str,
    api_base_url: str,
    console: Any,
    output_format: str = "table",
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """List app passwords via GET /api/auth/app-passwords. Returns True on success."""
    url = f"{api_base_url}/api/auth/app-passwords"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("appPasswords", data.get("passwords", []))
            if not isinstance(items, list):
                items = []
            if output_format == "json":
                print(json.dumps(items, indent=2))
                return True
            if RICH_AVAILABLE:
                table = Table(title="App Passwords")
                table.add_column("ID", style="cyan")
                table.add_column("NAME", style="green")
                table.add_column("CREATED", style="dim")
                table.add_column("ACTIVE", style="yellow")
                for item in items:
                    table.add_row(
                        str(item.get("id", "")),
                        str(item.get("name", "")),
                        str(item.get("createdAt", item.get("created_at", ""))),
                        "Yes" if item.get("isActive", item.get("is_active", True)) else "No",
                    )
                console.print(table)
            else:
                console.print("\nApp Passwords")
                console.print("=" * 70)
                console.print(f"{'ID':<38} {'NAME':<20} {'ACTIVE':<8}")
                console.print("=" * 70)
                for item in items:
                    console.print(f"{str(item.get('id', '')):<38} {str(item.get('name', '')):<20} {'Yes' if item.get('isActive', item.get('is_active', True)) else 'No':<8}")
                console.print("=" * 70)
            return True
        console.print(f"❌ Failed to list app passwords: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def app_password_delete(
    access_token: str,
    api_base_url: str,
    password_id: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Delete app password via DELETE /api/auth/app-passwords/{id}. Returns True on success."""
    url = f"{api_base_url}/api/auth/app-passwords/{password_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.delete(url, headers=headers, timeout=30)
        if response.status_code in (200, 204):
            console.print("✅ App password deleted.", style="green")
            return True
        console.print(f"❌ Failed to delete app password: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def agent_create(
    access_token: str,
    api_base_url: str,
    organization_id: str,
    name: str,
    console: Any,
    model: str = "gpt-4o",
    master_prompt: Optional[str] = None,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Create agent via POST /api/agents. Returns True on success."""
    url = f"{api_base_url}/api/agents"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    payload = {"organizationId": organization_id, "name": name, "model": model}
    if master_prompt is not None:
        payload["masterPrompt"] = master_prompt
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            agent = data.get("agent", data)
            aid = agent.get("id") if isinstance(agent, dict) else data.get("id")
            console.print(f"✅ Agent created. ID: {aid}", style="green")
            return True
        err = response.json() if response.text else {}
        console.print(f"❌ Failed to create agent: {response.status_code} {err.get('error', response.text)}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def agent_update(
    access_token: str,
    api_base_url: str,
    agent_id: str,
    console: Any,
    name: Optional[str] = None,
    temperature: Optional[float] = None,
    model: Optional[str] = None,
    master_prompt: Optional[str] = None,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Update agent via PUT /api/agents/{agentId}. Returns True on success."""
    url = f"{api_base_url}/api/agents/{agent_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    payload = {}
    if name is not None:
        payload["name"] = name
    if temperature is not None:
        payload["temperature"] = temperature
    if model is not None:
        payload["model"] = model
    if master_prompt is not None:
        payload["masterPrompt"] = master_prompt
    if not payload:
        console.print("❌ Provide at least one field to update (e.g. --agent-name, --agent-temperature)", style="red")
        return False
    try:
        response = requests.put(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.put(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            console.print("✅ Agent updated (new revision created).", style="green")
            return True
        err = response.json() if response.text else {}
        console.print(f"❌ Failed to update agent: {response.status_code} {err.get('error', response.text)}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def agent_delete(
    access_token: str,
    api_base_url: str,
    agent_id: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Delete agent via DELETE /api/agents/{agentId}. Returns True on success."""
    url = f"{api_base_url}/api/agents/{agent_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.delete(url, headers=headers, timeout=30)
        if response.status_code in (200, 204):
            console.print("✅ Agent deleted.", style="green")
            return True
        console.print(f"❌ Failed to delete agent: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def agent_show(
    access_token: str,
    api_base_url: str,
    agent_id: str,
    console: Any,
    output_format: str = "table",
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Show agent details via GET /api/agents/{agentId}. Returns True on success."""
    config = get_agent_config(access_token, agent_id, api_base_url, console, session_manager)
    if not config:
        return False
    if output_format == "json":
        print(json.dumps(config, indent=2))
        return True
    console.print(f"Agent: {config.get('agentName', 'N/A')}", style="green")
    console.print(f"  Model: {config.get('model', 'N/A')}", style="dim")
    console.print(f"  Temperature: {config.get('temperature', 'N/A')}", style="dim")
    console.print(f"  Max tokens: {config.get('maxTokens', 'N/A')}", style="dim")
    console.print(f"  Revision ID: {config.get('agentRevisionId', 'N/A')}", style="dim")
    if config.get("masterPrompt"):
        console.print(f"  Master prompt: {config['masterPrompt'][:80]}...", style="dim")
    return True


def mcp_list_servers(
    access_token: str,
    api_base_url: str,
    console: Any,
    output_format: str = "table",
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """List MCP servers via GET /api/mcp/servers. Returns True on success."""
    url = f"{api_base_url}/api/mcp/servers"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            servers = data.get("servers", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            if output_format == "json":
                print(json.dumps(servers, indent=2))
                return True
            if RICH_AVAILABLE:
                table = Table(title="MCP Servers")
                table.add_column("ID", style="cyan")
                table.add_column("NAME", style="green")
                table.add_column("STATUS", style="yellow")
                for s in servers:
                    table.add_row(str(s.get("id", "")), str(s.get("name", "")), str(s.get("status", "")))
                console.print(table)
            else:
                console.print("\nMCP Servers")
                console.print("=" * 60)
                for s in servers:
                    console.print(f"  {s.get('name', '')} ({s.get('status', '')})")
                console.print("=" * 60)
            return True
        console.print(f"❌ Failed to list MCP servers: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def mcp_tools(
    access_token: str,
    api_base_url: str,
    agent_id: str,
    console: Any,
    output_format: str = "table",
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """List MCP tool definitions for agent via GET /api/agents/{agentId}/mcp/tool-definitions. Returns True on success."""
    url = f"{api_base_url}/api/agents/{agent_id}/mcp/tool-definitions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            tools = data.get("tools", data.get("toolDefinitions", [])) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            if output_format == "json":
                print(json.dumps(tools, indent=2))
                return True
            console.print(f"MCP tools for agent {agent_id}:", style="green")
            for t in tools:
                name = t.get("name") or (t.get("function", {}) or {}).get("name", "?")
                desc = (t.get("function", {}) or {}).get("description", t.get("description", ""))
                console.print(f"  • {name}: {desc[:60]}..." if len(str(desc)) > 60 else f"  • {name}: {desc}", style="dim")
            return True
        console.print(f"❌ Failed to get MCP tools: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def mcp_health(
    access_token: str,
    api_base_url: str,
    agent_id: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Get MCP health for agent via GET /api/agents/{agentId}/mcp/health. Returns True on success."""
    url = f"{api_base_url}/api/agents/{agent_id}/mcp/health"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            console.print(f"MCP health for agent {agent_id}:", style="green")
            console.print(json.dumps(data, indent=2) if isinstance(data, dict) else str(data), style="dim")
            return True
        console.print(f"❌ MCP health check failed: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def billing_usage(
    access_token: str,
    api_base_url: str,
    console: Any,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    output_format: str = "table",
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Get user billing/usage via GET /api/billing/user. Returns True on success."""
    url = f"{api_base_url}/api/billing/user"
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, params=params or None, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, params=params or None, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if output_format == "json":
                print(json.dumps(data, indent=2))
                return True
            total = data.get("totalAgent700Cost", data.get("totalCost", 0))
            logs = data.get("billingLogs", [])
            console.print(f"Total cost: {total}", style="green")
            if logs and RICH_AVAILABLE:
                table = Table(title="Billing Logs")
                table.add_column("Model", style="cyan")
                table.add_column("Prompt Tokens", style="dim")
                table.add_column("Completion Tokens", style="dim")
                table.add_column("Cost", style="yellow")
                for log in logs[:20]:
                    table.add_row(
                        str(log.get("modelName", "")),
                        str(log.get("promptTokens", "")),
                        str(log.get("completionTokens", "")),
                        str(log.get("agent700Cost", "")),
                    )
                console.print(table)
            elif logs:
                for log in logs[:20]:
                    console.print(f"  {log.get('modelName')}: {log.get('agent700Cost')}", style="dim")
            return True
        console.print(f"❌ Failed to get billing: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def ratings_submit(
    access_token: str,
    api_base_url: str,
    agent_id: str,
    revision_id: int,
    score: int,
    console: Any,
    notes: Optional[str] = None,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Submit rating via POST /api/ratings. Returns True on success."""
    url = f"{api_base_url}/api/ratings"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    payload = {"agentId": agent_id, "agentRevisionId": revision_id, "rating": score}
    if notes:
        payload["notes"] = notes
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            console.print("✅ Rating submitted.", style="green")
            return True
        console.print(f"❌ Failed to submit rating: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def ratings_export(
    access_token: str,
    api_base_url: str,
    console: Any,
    output_file: Optional[str] = None,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Export ratings CSV via GET /api/ratings-export. Returns True on success."""
    url = f"{api_base_url}/api/ratings-export"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            content = response.text if hasattr(response, "text") else response.content.decode()
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(content)
                console.print(f"✅ Exported to {output_file}", style="green")
            else:
                print(content, end="")
            return True
        console.print(f"❌ Failed to export ratings: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def qa_sheets_list(
    access_token: str,
    api_base_url: str,
    agent_id: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """List QA sheets for agent via GET /api/agents/{agentId}/qa-sheets. Returns True on success."""
    url = f"{api_base_url}/api/agents/{agent_id}/qa-sheets"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            sheets = data if isinstance(data, list) else data.get("qaSheets", [])
            console.print(f"QA sheets for agent {agent_id}:", style="green")
            for s in sheets:
                console.print(f"  {s.get('id')} (revision {s.get('currentRevision', '')})", style="dim")
            return True
        console.print(f"❌ Failed to list QA sheets: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def parse_document(
    access_token: str,
    api_base_url: str,
    file_path: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Parse document via POST /api/helpers/parse-document (multipart). Returns True on success."""
    url = f"{api_base_url}/api/helpers/parse-document"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    path = Path(file_path)
    if not path.exists():
        console.print(f"❌ File not found: {file_path}", style="red")
        return False
    try:
        with open(path, "rb") as f:
            files = {"file": (path.name, f)}
            response = requests.post(url, headers=headers, files=files, timeout=60)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                with open(path, "rb") as f:
                    files = {"file": (path.name, f)}
                    response = requests.post(url, headers=headers, files=files, timeout=60)
        if response.status_code == 200:
            data = response.json()
            text = data.get("text", data.get("content", ""))
            print(text, end="")
            return True
        console.print(f"❌ Parse failed: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def context_library_list(
    access_token: str,
    api_base_url: str,
    console: Any,
    output_format: str = "table",
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """List context library (alignment data) via GET /api/alignment-data. Returns True on success."""
    url = f"{api_base_url}/api/alignment-data"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("data", [])
            if output_format == "json":
                print(json.dumps(items, indent=2))
                return True
            console.print("Context library:", style="green")
            for item in items:
                k = item.get("key", "")
                v = str(item.get("value", ""))
                console.print(f"  {k}: {v[:60]}..." if len(v) > 60 else f"  {k}: {v}", style="dim")
            return True
        console.print(f"❌ Failed to list context library: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def context_library_get(
    access_token: str,
    api_base_url: str,
    key: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Get context library value by key via GET /api/alignment-data/by-key/{key}. Returns True on success."""
    url = f"{api_base_url}/api/alignment-data/by-key/{key}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            value = data.get("value", data) if isinstance(data, dict) else data
            print(value)
            return True
        console.print(f"❌ Failed to get key: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def context_library_set(
    access_token: str,
    api_base_url: str,
    key: str,
    value: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Set context library key-value via POST /api/alignment-data. Returns True on success."""
    url = f"{api_base_url}/api/alignment-data"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    payload = {"key": key, "value": value}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            console.print("✅ Context library entry set.", style="green")
            return True
        console.print(f"❌ Failed to set: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def context_library_delete(
    access_token: str,
    api_base_url: str,
    key: str,
    console: Any,
    session_manager: Optional[SessionManager] = None,
) -> bool:
    """Delete context library entry via DELETE /api/alignment-data/{key}. Returns True on success."""
    url = f"{api_base_url}/api/alignment-data/{key}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0",
        "X-Device-Fingerprint": get_device_fingerprint(),
    }
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.delete(url, headers=headers, timeout=30)
        if response.status_code in (200, 204):
            console.print("✅ Context library entry deleted.", style="green")
            return True
        console.print(f"❌ Failed to delete: {response.status_code}", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        return False


def send_message_http(access_token: str, agent_uuid: str, user_message: str, 
                     api_base_url: str, agent_config: Dict[str, Any], 
                     conversation_manager: ConversationManager, console: Any, timeout: int = 300, silent: bool = False,
                     session_manager: Optional[SessionManager] = None) -> AgentResponse:
    """Send message via HTTP API and return response."""
    chat_url = f"{api_base_url}/api/chat"
    headers = {
        "Authorization": f"Bearer {access_token}", "Content-Type": "application/json",
        "User-Agent": "A700cli/1.0.0", "X-Device-Fingerprint": get_device_fingerprint()
    }
    
    messages = conversation_manager.to_api_messages()
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Build payload for HTTP API
    payload = {
        "agentId": agent_uuid,
        "messages": messages,
        "streamResponses": False
    }
    
    try:
        if not silent:
            console.print("💬 Sending request", style="blue", end="")
            
            # Start animated dots
            dots_running = True
            def animate_dots():
                while dots_running:
                    print(".", end="", flush=True)
                    time.sleep(0.5)
            
            dots_thread = threading.Thread(target=animate_dots, daemon=True)
            dots_thread.start()
        
        response = requests.post(chat_url, json=payload, headers=headers, timeout=timeout)
        
        if not silent:
            dots_running = False
            print()
        
        if response.status_code == 401 and session_manager:
            new_token = refresh_access_token(api_base_url, session_manager)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.post(chat_url, json=payload, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for API errors first
            if data.get('error'):
                return AgentResponse(content="", error=f"API Error: {data.get('error')}")
            
            # Try different possible response structures
            content = data.get('content') or data.get('message') or data.get('response')
            if not content and 'messages' in data:
                # Check if response is in messages array
                messages = data.get('messages', [])
                if messages:
                    last_message = messages[-1]
                    content = last_message.get('content', '')
            
            if content:
                conversation_manager.add_user_message(user_message)
                conversation_manager.add_agent_message(content)
                
                return AgentResponse(
                    content=content,
                    citations=data.get('citations', [])
                )
            else:
                return AgentResponse(content="", error=f"No content found in response: {data}")
        else:
            return AgentResponse(content="", error=f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        return AgentResponse(content="", error=str(e))

def main() -> None:
    """Main entry point for a700cli command."""
    parser = argparse.ArgumentParser(
        prog="a700cli",
        description="Enhanced Agent700 CLI with Interactive Configuration",
    )
    parser.add_argument(
        "message",
        nargs="?",
        help="Message to send. If omitted, use --input-file or pipe from stdin.",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Start interactive chat"
    )
    parser.add_argument(
        "--input-file",
        "-f",
        help="Read message from a file. Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--output-file", "-o", help="Write assistant response to a file (raw content)."
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Silence status logs and print only raw assistant content (good for piping).",
    )
    parser.add_argument(
        "--help-auth", action="store_true", help="Show auth-related env vars and exit"
    )
    parser.add_argument(
        "--streaming", action="store_true", help="Use WebSocket streaming mode (requires python-socketio)"
    )
    parser.add_argument(
        "--list-agents", "-l",
        action="store_true",
        help="List available agents with pagination and search"
    )
    parser.add_argument(
        "--list-orgs",
        action="store_true",
        help="List user's organizations (id, name, role)"
    )
    parser.add_argument(
        "--create-app-password",
        metavar="NAME",
        help="Create an app password (token shown once)",
    )
    parser.add_argument(
        "--list-app-passwords",
        action="store_true",
        help="List app passwords (no tokens)",
    )
    parser.add_argument(
        "--delete-app-password",
        metavar="ID",
        help="Delete an app password by ID",
    )
    parser.add_argument(
        "--create-agent",
        action="store_true",
        help="Create a new agent (requires --agent-org and --agent-name)",
    )
    parser.add_argument(
        "--agent-org",
        metavar="ORG_ID",
        help="Organization ID (required for --create-agent)",
    )
    parser.add_argument(
        "--agent-name",
        metavar="NAME",
        help="Agent name (for create/update)",
    )
    parser.add_argument(
        "--agent-model",
        metavar="MODEL",
        default="gpt-4o",
        help="Model for agent (default: gpt-4o)",
    )
    parser.add_argument(
        "--agent-prompt",
        metavar="TEXT",
        help="Master prompt for agent (create/update)",
    )
    parser.add_argument(
        "--agent-temperature",
        type=float,
        metavar="T",
        help="Temperature for agent (0-1, update)",
    )
    parser.add_argument(
        "--update-agent",
        metavar="AGENT_ID",
        help="Update agent by ID (creates new revision)",
    )
    parser.add_argument(
        "--delete-agent",
        metavar="AGENT_ID",
        help="Delete agent by ID",
    )
    parser.add_argument(
        "--show-agent",
        metavar="AGENT_ID",
        help="Show agent details by ID",
    )
    parser.add_argument(
        "--list-mcp-servers",
        action="store_true",
        help="List MCP servers",
    )
    parser.add_argument(
        "--mcp-tools",
        metavar="AGENT_ID",
        help="List MCP tool definitions for an agent",
    )
    parser.add_argument(
        "--mcp-health",
        metavar="AGENT_ID",
        help="MCP health status for an agent",
    )
    parser.add_argument(
        "--billing-usage",
        action="store_true",
        help="Show billing/usage (optional --start-date, --end-date)",
    )
    parser.add_argument(
        "--start-date",
        metavar="YYYY-MM-DD",
        help="Start date for billing (with --billing-usage)",
    )
    parser.add_argument(
        "--end-date",
        metavar="YYYY-MM-DD",
        help="End date for billing (with --billing-usage)",
    )
    parser.add_argument(
        "--rate",
        action="store_true",
        help="Submit a rating (requires --agent-id, --revision-id, --score)",
    )
    parser.add_argument(
        "--agent-id",
        metavar="ID",
        help="Agent ID (for --rate)",
    )
    parser.add_argument(
        "--revision-id",
        type=int,
        metavar="N",
        help="Agent revision ID (for --rate)",
    )
    parser.add_argument(
        "--score",
        type=int,
        metavar="N",
        help="Rating score (for --rate)",
    )
    parser.add_argument(
        "--rating-notes",
        metavar="TEXT",
        help="Optional notes for rating (with --rate)",
    )
    parser.add_argument(
        "--export-ratings",
        action="store_true",
        help="Export ratings as CSV (to stdout or --output-file)",
    )
    parser.add_argument(
        "--qa-sheets",
        metavar="AGENT_ID",
        help="List QA sheets for an agent",
    )
    parser.add_argument(
        "--parse-document",
        metavar="FILE",
        help="Parse document (PDF/DOCX/etc.) and print extracted text",
    )
    parser.add_argument(
        "--context-library-list",
        action="store_true",
        help="List context library entries",
    )
    parser.add_argument(
        "--context-library-get",
        metavar="KEY",
        help="Get context library value by key",
    )
    parser.add_argument(
        "--context-library-set",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Set context library key-value (KEY VALUE)",
    )
    parser.add_argument(
        "--context-library-delete",
        metavar="KEY",
        help="Delete context library entry by key",
    )
    parser.add_argument(
        "--page", type=int, default=1,
        help="Page number for agent list (used with --list-agents)"
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Results per page (default: 20, max: 100, used with --list-agents)"
    )
    parser.add_argument(
        "--search", type=str,
        help="Filter agents by name (case-insensitive, used with --list-agents)"
    )
    parser.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="Output format for --list-agents (default: table)"
    )
    parser.add_argument(
        "--version", action="version", version=f"a700cli {__import__('a700cli').__version__}"
    )
    parser.add_argument(
        "--llm-wiki-init",
        action="store_true",
        help="Create local llm-wiki scaffold (raw/, wiki/, intake/, AGENTS.md, index.md, log.md). No API auth.",
    )
    parser.add_argument(
        "--llm-wiki-ingest-url",
        metavar="URL",
        default=None,
        help="Record a URL ingest under raw/sources/<id>/ with manifest.json; update wiki index and log. No API auth.",
    )
    parser.add_argument(
        "--llm-wiki-ingest-file",
        metavar="PATH",
        default=None,
        help="Copy a file into raw/sources/<id>/ with manifest.json; update wiki index and log. No API auth.",
    )
    parser.add_argument(
        "--llm-wiki-root",
        type=Path,
        default=None,
        help="Root directory for llm-wiki commands (default: current working directory).",
    )
    parser.add_argument(
        "--llm-wiki-fetch",
        action="store_true",
        help="With --llm-wiki-ingest-url, attempt to download response bytes into raw/ (errors recorded in manifest).",
    )
    parser.add_argument(
        "--llm-wiki-category",
        metavar="NAME",
        default=None,
        help="Optional category label stored in manifest for --llm-wiki-ingest-file.",
    )
    args = parser.parse_args()

    wiki_cmds = (
        int(bool(args.llm_wiki_init))
        + int(args.llm_wiki_ingest_url is not None)
        + int(args.llm_wiki_ingest_file is not None)
    )
    if wiki_cmds > 1:
        parser.error(
            "Use only one of --llm-wiki-init, --llm-wiki-ingest-url, --llm-wiki-ingest-file"
        )
    if args.llm_wiki_init or args.llm_wiki_ingest_url or args.llm_wiki_ingest_file:
        from a700cli import llm_wiki as _llm_wiki

        root = args.llm_wiki_root
        try:
            if args.llm_wiki_init:
                info = _llm_wiki.init_wiki(root)
                print(f"Initialized LLM wiki at {info['root']}")
                if info.get("created_dirs"):
                    print("Created directories:", ", ".join(info["created_dirs"]))
            elif args.llm_wiki_ingest_url:
                info = _llm_wiki.ingest_url(
                    root, args.llm_wiki_ingest_url, fetch=args.llm_wiki_fetch
                )
                print(f"Recorded URL ingest source_id={info['source_id']}")
                print(f"  manifest: {info['manifest']}")
                print(f"  wiki:     {info['wiki_page']}")
            else:
                info = _llm_wiki.ingest_file(
                    root,
                    Path(args.llm_wiki_ingest_file),
                    category=args.llm_wiki_category,
                )
                print(f"Recorded file ingest source_id={info['source_id']}")
                print(f"  manifest: {info['manifest']}")
                print(f"  wiki:     {info['wiki_page']}")
        except _llm_wiki.LlmWikiError as e:
            print(f"llm-wiki error: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    if args.help_auth:
        print("Uses env vars: API_BASE_URL, EMAIL, PASSWORD, AGENT_UUID")
        sys.exit(0)
    
    # Handle list-agents command early (before reading message input)
    if args.list_agents:
        # We'll handle this after authentication
        pass
    
    console = Console()
    # Quiet mode swap for console
    if args.quiet and not args.interactive:
        if not RICH_AVAILABLE:
            console = SilentConsole()
        else:
            # For Rich, we'll handle quiet mode differently
            class QuietConsole(Console):
                def print(self, *args, **kwargs):
                    if kwargs.get('end') != '':
                        super().print(*args, **kwargs)
                def print_panel(self, *args, **kwargs):
                    pass
            console = QuietConsole()
    
    session_manager = SessionManager()
    conversation_manager = ConversationManager()
    
    env = load_environment()
    api_base_url = env.get("API_BASE_URL", "https://api.agent700.ai")
    
    email = env.get("EMAIL")
    password = env.get("PASSWORD")
    agent_uuid = env.get("AGENT_UUID")
    
    # Read message from CLI, file, or stdin if not interactive
    user_message = None
    if not args.interactive:
        if args.message:
            user_message = args.message
        elif args.input_file:
            if args.input_file == "-":
                user_message = sys.stdin.read()
            else:
                try:
                    with open(args.input_file, "r", encoding="utf-8") as f:
                        user_message = f.read()
                except FileNotFoundError:
                    console.print(f"❌ Error: Input file not found: {args.input_file}", style="red")
                    sys.exit(1)
                except Exception as e:
                    console.print(f"❌ Error reading input file: {e}", style="red")
                    sys.exit(1)
        elif not sys.stdin.isatty():
            user_message = sys.stdin.read()
    
    if not email:
        email = input("📧 Email: ").strip()
        if not email:
            console.print("❌ Email is required", style="red")
            sys.exit(1)
    
    if not password:
        try:
            import getpass
            password = getpass.getpass("🔐 Password: ")
        except (EOFError, KeyboardInterrupt):
            # Fallback to regular input if getpass fails
            password = input("🔐 Password: ")
        if not password:
            console.print("❌ Password is required", style="red")
            sys.exit(1)
    
    auth_result = authenticate(email, password, api_base_url, console)
    if not auth_result:
        console.print("❌ Authentication failed", style="red")
        sys.exit(1)
    if isinstance(auth_result, tuple):
        access_token, cookies = auth_result
    else:
        access_token = auth_result
        cookies = {}
    session_manager.save_session({
        "access_token": access_token, "email": email,
        "cookies": cookies,
        "saved_at": datetime.now().isoformat()
    })
    
    # Handle list-agents command
    if args.list_agents:
        list_agents(
            access_token,
            api_base_url,
            console,
            page=args.page,
            limit=args.limit,
            search=args.search,
            output_format=args.format,
            session_manager=session_manager,
        )
        sys.exit(0)
    
    # Handle list-orgs command
    if args.list_orgs:
        list_orgs(
            access_token,
            api_base_url,
            console,
            output_format=args.format,
            session_manager=session_manager,
        )
        sys.exit(0)
    
    # Handle app password commands
    if args.create_app_password:
        ok = app_password_create(
            access_token, api_base_url, args.create_app_password, console, session_manager
        )
        sys.exit(0 if ok else 1)
    if args.list_app_passwords:
        ok = app_password_list(
            access_token, api_base_url, console, output_format=args.format, session_manager=session_manager
        )
        sys.exit(0 if ok else 1)
    if args.delete_app_password:
        ok = app_password_delete(
            access_token, api_base_url, args.delete_app_password, console, session_manager
        )
        sys.exit(0 if ok else 1)
    
    # Handle agent CRUD
    if args.create_agent:
        if not args.agent_org or not args.agent_name:
            console.print("❌ --create-agent requires --agent-org and --agent-name", style="red")
            sys.exit(1)
        ok = agent_create(
            access_token, api_base_url, args.agent_org, args.agent_name, console,
            model=args.agent_model or "gpt-4o",
            master_prompt=args.agent_prompt,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.update_agent:
        ok = agent_update(
            access_token, api_base_url, args.update_agent, console,
            name=args.agent_name,
            temperature=args.agent_temperature,
            model=args.agent_model,
            master_prompt=args.agent_prompt,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.delete_agent:
        ok = agent_delete(access_token, api_base_url, args.delete_agent, console, session_manager)
        sys.exit(0 if ok else 1)
    if args.show_agent:
        ok = agent_show(
            access_token, api_base_url, args.show_agent, console,
            output_format=args.format,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    
    # Handle MCP commands
    if args.list_mcp_servers:
        ok = mcp_list_servers(
            access_token, api_base_url, console,
            output_format=args.format,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.mcp_tools:
        ok = mcp_tools(
            access_token, api_base_url, args.mcp_tools, console,
            output_format=args.format,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.mcp_health:
        ok = mcp_health(
            access_token, api_base_url, args.mcp_health, console,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    
    if args.billing_usage:
        ok = billing_usage(
            access_token, api_base_url, console,
            start_date=args.start_date,
            end_date=args.end_date,
            output_format=args.format,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.rate:
        if not args.agent_id or args.revision_id is None or args.score is None:
            console.print("❌ --rate requires --agent-id, --revision-id, and --score", style="red")
            sys.exit(1)
        ok = ratings_submit(
            access_token, api_base_url, args.agent_id, args.revision_id, args.score, console,
            notes=args.rating_notes,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.export_ratings:
        ok = ratings_export(
            access_token, api_base_url, console,
            output_file=args.output_file,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.qa_sheets:
        ok = qa_sheets_list(
            access_token, api_base_url, args.qa_sheets, console,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.parse_document:
        ok = parse_document(
            access_token, api_base_url, args.parse_document, console,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.context_library_list:
        ok = context_library_list(
            access_token, api_base_url, console,
            output_format=args.format,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.context_library_get:
        ok = context_library_get(
            access_token, api_base_url, args.context_library_get, console,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.context_library_set:
        key, value = args.context_library_set[0], args.context_library_set[1]
        ok = context_library_set(
            access_token, api_base_url, key, value, console,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    if args.context_library_delete:
        ok = context_library_delete(
            access_token, api_base_url, args.context_library_delete, console,
            session_manager=session_manager,
        )
        sys.exit(0 if ok else 1)
    
    # Track if UUID was just set up (for auto-interactive mode) (SPEC-AUTO-INTERACTIVE-001)
    uuid_just_setup = False
    
    if not agent_uuid:
        console.print("🔍 No agent UUID found. Enter an agent UUID to continue.", style="blue")
        console.print("💡 Tip: Use 'a700cli --list-agents' to see available agents.", style="dim")
        agent_uuid = prompt_agent_uuid(console)
        if not agent_uuid:
            console.print("❌ No agent UUID provided", style="red")
            sys.exit(1)
        
        # Validate UUID exists by fetching agent config
        agent_config = get_agent_config(access_token, agent_uuid, api_base_url, console, session_manager)
        if not agent_config:
            console.print("❌ Failed to load agent. Please verify the UUID is correct.", style="red")
            sys.exit(1)
        
        # Save to .env file
        try:
            env_content = f"API_BASE_URL={api_base_url}\nEMAIL={email}\nPASSWORD={password}\nAGENT_UUID={agent_uuid}\n"
            with open(".env", "w") as f:
                f.write(env_content)
            console.print("✅ Configuration saved to .env file", style="green")
            uuid_just_setup = True  # Track that we just set this up (SPEC-AUTO-INTERACTIVE-001)
        except Exception as e:
            console.print("⚠️ Could not save configuration to .env file", style="yellow")
            uuid_just_setup = False
    else:
        uuid_just_setup = False  # UUID was already in .env (SPEC-AUTO-INTERACTIVE-001)
        # Agent UUID exists in .env, fetch config
        agent_config = get_agent_config(access_token, agent_uuid, api_base_url, console, session_manager)
        if not agent_config:
            console.print("❌ Failed to load agent. Please verify the UUID in .env is correct.", style="red")
            console.print("💡 Tip: Use 'a700cli --list-agents' to see available agents.", style="dim")
            sys.exit(1)
    
    # Agent configuration loaded
    interactive_mode = args.interactive
    
    # Auto-enter interactive mode if UUID was just set up and no message provided (SPEC-AUTO-INTERACTIVE-001)
    if uuid_just_setup and not user_message and not args.interactive:
        console.print("💬 Starting interactive chat with streaming...", style="blue")
        interactive_mode = True
        # Enable streaming for auto-entered interactive mode (SPEC-AUTO-INTERACTIVE-001)
        args.streaming = True
    
    if interactive_mode:
        console.print_panel(
            "Interactive Agent700 Chat\n\nCommands: /exit, /quit, /q, /clear, /context, /help",
            title="Interactive Chat", style="green"
        )
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['/exit', '/quit', '/q']:
                    console.print("👋 Goodbye!", style="green")
                    break
                elif user_input.lower() == '/clear':
                    conversation_manager.clear()
                    console.print("🧹 Conversation history cleared", style="yellow")
                    continue
                elif user_input.lower() == '/context':
                    context = conversation_manager.get_conversation_context()
                    if not context:
                        console.print("ℹ️ No conversation history yet", style="dim")
                    else:
                        console.print("🧠 Recent context:", style="cyan")
                        for message in context:
                            role = message.get('role', 'unknown').upper()
                            content = message.get('content', '')
                            preview = content if len(content) <= 120 else f"{content[:117]}..."
                            console.print(f"  [{role}] {preview}", style="dim")
                    continue
                elif user_input.lower() == '/help':
                    console.print(
                        "Commands: /exit, /quit, /q, /clear, /context, /help",
                        style="dim",
                    )
                    continue
                
                if not user_input: continue
                
                console.print("🤖 Agent: ", style="blue", end="")
                
                # Use WebSocket if available and requested, otherwise HTTP
                if args.streaming and WEBSOCKET_AVAILABLE:
                    try:
                        ws_client = WebSocketClient(api_base_url, access_token, console)
                        response_data = ws_client.send_message(agent_uuid, user_input, agent_config, conversation_manager)
                        if response_data.error and "Connection failed" in response_data.error:
                            # Fallback to HTTP
                            response_data = send_message_http(access_token, agent_uuid, user_input, 
                                                            api_base_url, agent_config, conversation_manager, console, session_manager=session_manager)
                    except Exception as e:
                        console.print(f"🔄 WebSocket error, falling back to HTTP: {e}", style="yellow")
                        response_data = send_message_http(access_token, agent_uuid, user_input, 
                                                        api_base_url, agent_config, conversation_manager, console, session_manager=session_manager)
                else:
                    response_data = send_message_http(access_token, agent_uuid, user_input, 
                                                    api_base_url, agent_config, conversation_manager, console)
                
                if response_data and not response_data.error:
                    console.print(response_data.content, style="white")
                    if response_data.citations:
                        console.print(f"\n📚 Sources: {', '.join(response_data.citations)}", style="dim")
                else:
                    console.print("❌ Failed to get response from agent", style="red")
                    if response_data and response_data.error:
                        console.print(f"Error: {response_data.error}", style="red")
                        
            except KeyboardInterrupt:
                console.print("\n👋 Goodbye!", style="green")
                break
            except Exception as e:
                console.print(f"❌ Error: {e}", style="red")
    else:
        if not user_message:
            console.print("❌ No message provided", style="red")
            print(
                'Usage: a700cli "msg" | a700cli -f prompt.txt | echo "hi" | a700cli -q',
                flush=True,
            )
            sys.exit(1)
        
        if not args.quiet:
            console.print(f"👤 You: {user_message}", style="white")
        
        # Use WebSocket if available and requested, otherwise HTTP
        if args.streaming and WEBSOCKET_AVAILABLE:
            try:
                ws_client = WebSocketClient(api_base_url, access_token, console)
                response_data = ws_client.send_message(agent_uuid, user_message, agent_config, conversation_manager)
                if response_data.error and "Connection failed" in response_data.error:
                    # Fallback to HTTP
                    if not args.quiet:
                        console.print("🔄 WebSocket failed, falling back to HTTP...", style="yellow")
                    response_data = send_message_http(access_token, agent_uuid, user_message, 
                                                    api_base_url, agent_config, conversation_manager, console, silent=args.quiet, session_manager=session_manager)
            except Exception as e:
                if not args.quiet:
                    console.print(f"🔄 WebSocket error, falling back to HTTP: {e}", style="yellow")
                response_data = send_message_http(access_token, agent_uuid, user_message, 
                                                api_base_url, agent_config, conversation_manager, console, silent=args.quiet)
        else:
            if args.streaming and not WEBSOCKET_AVAILABLE and not args.quiet:
                console.print("⚠ WebSocket not available, using HTTP mode", style="yellow")
            response_data = send_message_http(access_token, agent_uuid, user_message, 
                                            api_base_url, agent_config, conversation_manager, console, silent=args.quiet, session_manager=session_manager)
        
        if response_data and not response_data.error:
            content = response_data.content or ""
            if args.output_file:
                try:
                    with open(args.output_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    if not args.quiet:
                        console.print(
                            f"✅ Wrote response to {args.output_file}", style="green"
                        )
                except Exception as e:
                    console.print(f"❌ Failed to write output file: {e}", style="red")
            else:
                if args.quiet:
                    print(content, end="")
                else:
                    console.print(f"🤖 Agent: {content}", style="white")
                    if response_data.citations:
                        console.print(
                            f"\n📚 Sources: {', '.join(response_data.citations)}",
                            style="dim",
                        )
        else:
            console.print("❌ Failed to get response from agent", style="red")
            if response_data and response_data.error:
                console.print(f"Error: {response_data.error}", style="red")
                sys.exit(1)

if __name__ == "__main__":
    main()