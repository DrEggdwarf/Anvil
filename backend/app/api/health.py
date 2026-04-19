"""Health check routes — system and tool availability."""

from __future__ import annotations

import importlib.util
import shutil

from backend.app.core.config import settings
from backend.app.models.tools import TOOL_DEFINITIONS, ToolKind, ToolStatus
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    """Basic health check."""
    return {"status": "ok", "version": settings.version}


@router.get("/health/detailed")
async def health_detailed():
    """Detailed health check with tool availability."""
    tools: dict[str, dict] = {}
    for tool_def in TOOL_DEFINITIONS:
        status = _check_tool(tool_def.name, tool_def.kind, tool_def.check_command)
        tools[tool_def.name] = status.model_dump()
    return {"status": "ok", "version": settings.version, "tools": tools}


@router.get("/tools")
async def list_tools():
    """List all tools grouped by category with availability."""
    by_category: dict[str, list[dict]] = {}
    for tool_def in TOOL_DEFINITIONS:
        cat = tool_def.category.value
        if cat not in by_category:
            by_category[cat] = []

        status = _check_tool(tool_def.name, tool_def.kind, tool_def.check_command)
        by_category[cat].append({
            **tool_def.model_dump(),
            "available": status.available,
            "path": status.path,
        })
    return {"tools": by_category}


@router.get("/tools/{mode}")
async def tools_for_mode(mode: str):
    """List tools required/optional for a specific mode."""
    tools = []
    for tool_def in TOOL_DEFINITIONS:
        if mode in tool_def.modes:
            status = _check_tool(tool_def.name, tool_def.kind, tool_def.check_command)
            tools.append({
                **tool_def.model_dump(),
                "available": status.available,
                "path": status.path,
            })
    return {"mode": mode, "tools": tools}


def _check_tool(name: str, kind: ToolKind, check_command: str) -> ToolStatus:
    """Check a single tool's availability."""
    if kind == ToolKind.SYSTEM_BINARY:
        path = shutil.which(check_command)
        return ToolStatus(name=name, available=path is not None, path=path)
    elif kind == ToolKind.PYTHON_PACKAGE:
        spec = importlib.util.find_spec(check_command)
        return ToolStatus(name=name, available=spec is not None)
    return ToolStatus(name=name, available=False)
