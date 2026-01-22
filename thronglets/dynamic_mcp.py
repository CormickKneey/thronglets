"""Dynamic MCP - Tool discovery and execution for Apps.

This module provides functions to discover and execute MCP tools from Apps.
Uses direct HTTP calls with SSE support for compatibility with MCP servers.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# Tool list cache for Apps (TTL: 5 minutes)
_tools_cache: dict[str, tuple[datetime, list[dict[str, Any]]]] = {}
_tools_cache_ttl = 300.0  # 5 minutes


async def get_app_tools(app_id: str, mcp_endpoint: str) -> list[dict[str, Any]]:
    """Get tools list from an App's MCP endpoint with caching.

    Args:
        app_id: The app ID (used as cache key).
        mcp_endpoint: The MCP endpoint URL.

    Returns:
        List of tool definitions.
    """
    # Check cache
    if app_id in _tools_cache:
        cached_time, tools = _tools_cache[app_id]
        if (datetime.now() - cached_time).total_seconds() < _tools_cache_ttl:
            return tools

    # Fetch from App
    try:
        logger.info(f"Fetching tools from app {app_id} at {mcp_endpoint}")

        try:
            async with asyncio.timeout(30.0):
                # Create httpx client with required headers for SSE
                headers = {
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                }

                async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                    # Initialize MCP session
                    init_request = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {
                                "name": "Thronglets ServiceBus",
                                "version": "0.1.0",
                            },
                        },
                    }

                    response = await client.post(mcp_endpoint, json=init_request)

                    if response.status_code != 200:
                        logger.error(
                            f"Initialize request failed: {response.status_code}"
                        )
                        return []

                    # Extract session ID from response headers
                    session_id = response.headers.get(
                        "mcp-session-id"
                    ) or response.headers.get("x-session-id")

                    if not session_id:
                        logger.error("No session ID found in response headers")
                        return []

                    logger.info(f"Session established: {session_id}")

                    # Call tools/list with session ID
                    tools_request = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {},
                    }

                    session_headers = headers.copy()
                    session_headers["mcp-session-id"] = session_id

                    tools_response = await client.post(
                        mcp_endpoint, json=tools_request, headers=session_headers
                    )

                    if tools_response.status_code != 200:
                        logger.error(
                            f"Tools request failed: {tools_response.status_code}"
                        )
                        return []

                    # Parse SSE response
                    tools_content = tools_response.text
                    if "data: " not in tools_content:
                        logger.error("Invalid SSE response format")
                        return []

                    tools_json_data = tools_content.split("data: ")[1].strip()
                    tools_result = json.loads(tools_json_data)

                    tools = tools_result.get("result", {}).get("tools", [])
                    processed_tools = [
                        {
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                            "inputSchema": tool.get("inputSchema", {}),
                        }
                        for tool in tools
                        if tool is not None
                    ]

                    logger.info(
                        f"Successfully fetched {len(processed_tools)} tools from {app_id}"
                    )

                    # Cache result
                    _tools_cache[app_id] = (datetime.now(), processed_tools)

                    return processed_tools

        except asyncio.TimeoutError:
            logger.error(f"Timeout while connecting to MCP endpoint: {mcp_endpoint}")
            return []

    except Exception as e:
        logger.error(
            f"Failed to get tools from app {app_id}: {e}, endpoint: {mcp_endpoint}"
        )
        logger.error(f"Exception type: {type(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def clear_tools_cache(app_id: str | None = None) -> None:
    """Clear the tools cache.

    Args:
        app_id: If provided, clear only this app's cache. Otherwise clear all.
    """
    if app_id is None:
        _tools_cache.clear()
    else:
        _tools_cache.pop(app_id, None)
