import asyncio
import platform
import os
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timezone
import pydantic

class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: Dict[str, Any],
        handler: Callable,
        required_permissions: List[str] = None,
        timeout_seconds: float = 30.0,
        is_sensitive: bool = False
    ):
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        self.handler = handler
        self.required_permissions = required_permissions or []
        self.timeout_seconds = timeout_seconds
        self.is_sensitive = is_sensitive

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters_schema": t.parameters_schema,
                "required_permissions": t.required_permissions,
                "is_sensitive": t.is_sensitive,
                "timeout_seconds": t.timeout_seconds
            }
            for t in self._tools.values()
        ]

    async def execute(self, tool_name: str, parameters: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        tool = self.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' is not registered")

        # Check permissions if user context provided
        if context and tool.required_permissions:
            user_roles = context.get("roles", [])
            user_perms = context.get("permissions", [])
            if "admin" not in user_roles:
                for req in tool.required_permissions:
                    if req not in user_perms:
                        raise PermissionError(f"Missing required permission '{req}' for tool '{tool_name}'")

        # Execute with timeout
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await asyncio.wait_for(tool.handler(parameters, context), timeout=tool.timeout_seconds)
            else:
                result = await asyncio.wait_for(asyncio.to_thread(tool.handler, parameters, context), timeout=tool.timeout_seconds)
            return {"success": True, "output": result}
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool '{tool_name}' timed out after {tool.timeout_seconds}s")
        except Exception as e:
            return {"success": False, "error": str(e)}

# Instantiate global registry
tool_registry = ToolRegistry()

# ================= Built-in Tool Implementations =================

async def system_info_handler(params: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    return {
        "os": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "nominal"
    }

tool_registry.register(ToolDefinition(
    name="system_info",
    description="Retrieve local system OS architecture, hardware metrics, and runtime status",
    parameters_schema={"type": "object", "properties": {}},
    handler=system_info_handler,
    required_permissions=["system:read"]
))

async def weather_handler(params: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    location = params.get("location", "Current Location")
    # Clean realistic weather metrics matching Friday UI aesthetics
    return {
        "location": location,
        "temperature_celsius": 21.5,
        "condition": "CLEAR",
        "humidity_percent": 58,
        "pressure_hpa": 1016,
        "wind_kmh": 12.4
    }

tool_registry.register(ToolDefinition(
    name="get_weather",
    description="Retrieve atmospheric and weather metrics for a specified location",
    parameters_schema={
        "type": "object",
        "properties": {"location": {"type": "string", "description": "City or locality"}},
    },
    handler=weather_handler
))

async def summarize_doc_handler(params: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    content = params.get("content", "")
    max_sentences = params.get("max_sentences", 3)
    if not content:
        return {"summary": "No text provided to summarize.", "word_count": 0}

    words = content.split()
    sentences = [s.strip() for s in content.replace("\n", " ").split(".") if s.strip()]
    selected = sentences[:max_sentences]
    summary_text = ". ".join(selected) + ("." if selected else "")
    return {
        "summary": summary_text,
        "original_word_count": len(words),
        "key_takeaways": selected
    }

tool_registry.register(ToolDefinition(
    name="summarize_text",
    description="Analyze and summarize document or text content into concise bullet takeaways",
    parameters_schema={
        "type": "object",
        "required": ["content"],
        "properties": {
            "content": {"type": "string", "description": "Text content to summarize"},
            "max_sentences": {"type": "integer", "default": 3}
        }
    },
    handler=summarize_doc_handler
))

async def open_app_handler(params: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    app_name = params.get("app_name", "").lower().strip()
    # Security: approved applications whitelist only
    approved_apps = {
        "chrome": "google-chrome",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "terminal": "powershell.exe",
        "edge": "msedge.exe",
        "code": "code"
    }

    if app_name not in approved_apps:
        return {
            "status": "rejected",
            "message": f"Application '{app_name}' is not in the approved whitelist. Allowed: {list(approved_apps.keys())}"
        }

    return {
        "status": "command_queued",
        "target_app": app_name,
        "executable": approved_apps[app_name],
        "message": f"Request to launch '{app_name}' acknowledged for Windows client agent."
    }

tool_registry.register(ToolDefinition(
    name="open_application",
    description="Queue an authorized desktop application launch on the local Windows agent",
    parameters_schema={
        "type": "object",
        "required": ["app_name"],
        "properties": {"app_name": {"type": "string", "description": "Name of approved app (e.g. chrome, notepad, calculator)"}}
    },
    handler=open_app_handler,
    required_permissions=["device:execute"],
    is_sensitive=True
))
