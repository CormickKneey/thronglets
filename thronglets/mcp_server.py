"""MCP Server for agent-to-agent communication."""

from datetime import datetime

from fastapi.logger import logger
from fastmcp import Context, FastMCP

from thronglets.models import (
    InternalMessage,
    Message,
    Part,
    Role,
    Task,
    TaskState,
    TaskStatus,
)
from thronglets.store import store

# Header key for agent ID
AGENT_ID_HEADER = "X-Agent-ID"


mcp = FastMCP(
    name="Thronglets MCP",
    instructions="MCP server for agent communication in Thronglets ServiceBus",
)


def get_agent_id_from_context(ctx: Context) -> str | None:
    """Extract agent_id from MCP context metadata."""
    if ctx.request_context and ctx.request_context.meta:
        meta = ctx.request_context.meta
        if hasattr(meta, "get"):
            return meta.get(AGENT_ID_HEADER) or meta.get("agent_id")
        if hasattr(meta, AGENT_ID_HEADER):
            return getattr(meta, AGENT_ID_HEADER)
        if hasattr(meta, "agent_id"):
            return getattr(meta, "agent_id")
    from fastmcp.server.dependencies import get_http_headers

    headers = get_http_headers()
    if headers and AGENT_ID_HEADER in headers:
        return headers[AGENT_ID_HEADER]
    if headers and AGENT_ID_HEADER.lower() in headers:
        return headers[AGENT_ID_HEADER.lower()]
    return None


# ============ Agent Tools ============


@mcp.tool()
def agent__list(ctx: Context) -> dict:
    """List all registered agents in the ServiceBus.

    Returns a list of all agents with their IDs, names, descriptions, and capabilities.
    """
    agents = store.list_agents()
    current_agent_id = get_agent_id_from_context(ctx)
    return {
        "current_agent_id": current_agent_id,
        "agents": [
            {
                "agent_id": agent.agent_id,
                "name": agent.card.name,
                "description": agent.card.description,
                "version": agent.card.version,
                "is_self": agent.agent_id == current_agent_id,
                "skills": [
                    {
                        "id": skill.id,
                        "name": skill.name,
                        "description": skill.description,
                        "tags": skill.tags,
                    }
                    for skill in agent.card.skills
                ],
                "supported_interfaces": [
                    {
                        "url": iface.url,
                        "protocol_binding": iface.protocol_binding,
                    }
                    for iface in agent.card.supported_interfaces
                ],
                "registered_at": agent.registered_at.isoformat(),
            }
            for agent in agents
        ],
        "total": len(agents),
    }


@mcp.tool()
def agent__whoami(ctx: Context) -> dict:
    """Get the current agent's information.

    Returns the current agent's ID and registration details based on the X-Agent-ID header.
    """
    agent_id = get_agent_id_from_context(ctx)
    if not agent_id:
        return {
            "status": "error",
            "error": "No agent_id found in context. Make sure X-Agent-ID header is set.",
        }

    agent = store.get_agent(agent_id)
    if not agent:
        return {
            "status": "error",
            "error": f"Agent with ID '{agent_id}' not found in registry.",
        }

    return {
        "status": "ok",
        "agent_id": agent.agent_id,
        "name": agent.card.name,
        "description": agent.card.description,
        "version": agent.card.version,
        "registered_at": agent.registered_at.isoformat(),
    }


# ============ Message Tools ============


@mcp.tool()
def message__send(
    ctx: Context,
    to_agent_id: str,
    content: str,
    task_id: str | None = None,
    context_id: str | None = None,
) -> dict:
    """Send a message to another agent.

    The sender agent ID is automatically determined from the X-Agent-ID header.

    Args:
        to_agent_id: The ID of the target agent to send the message to.
        content: The text content of the message.
        task_id: Optional task ID to associate the message with.
        context_id: Optional context ID for the conversation.

    Returns:
        Status of the message delivery.
    """
    from_agent_id = get_agent_id_from_context(ctx)

    target_agent = store.get_agent(to_agent_id)
    if not target_agent:
        return {
            "status": "error",
            "error": f"Agent with ID '{to_agent_id}' not found",
        }

    message = Message(
        role=Role.AGENT,
        parts=[Part(text=content)],
        task_id=task_id,
        context_id=context_id,
    )

    internal_msg = InternalMessage(
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        message=message,
    )
    store.send_message(internal_msg)
    logger.info(f"SENT <{from_agent_id} -> {to_agent_id}> :{content}")

    if task_id:
        task = store.get_task(task_id)
        if task:
            task.history.append(message)
            store.update_task(task)

    return {
        "status": "sent",
        "message_id": internal_msg.id,
        "from_agent_id": from_agent_id,
        "to_agent": {
            "id": target_agent.agent_id,
            "name": target_agent.card.name,
        },
    }


@mcp.tool()
def message__receive(
    ctx: Context,
    mark_as_read: bool = True,
    limit: int = 100,
) -> dict:
    """Receive messages sent to this agent.

    The agent ID is automatically determined from the X-Agent-ID header.

    Args:
        mark_as_read: Whether to mark retrieved messages as read (default: True).
        limit: Maximum number of messages to retrieve (default: 100).

    Returns:
        List of unread messages for the agent.
    """
    agent_id = get_agent_id_from_context(ctx)
    if not agent_id:
        return {
            "status": "error",
            "error": "No agent_id found in context. Make sure X-Agent-ID header is set.",
        }

    agent = store.get_agent(agent_id)
    if not agent:
        return {
            "status": "error",
            "error": f"Agent with ID '{agent_id}' not found",
        }

    messages = store.receive_messages(
        agent_id=agent_id,
        mark_as_read=mark_as_read,
        limit=limit,
    )
    if len(messages) > 0:
        logger.info(
            f"RECEIVED <{messages[0].from_agent_id} -> {agent_id}> :{messages[0].message.parts[0].text}"
        )

    return {
        "status": "ok",
        "agent_id": agent_id,
        "messages": [
            {
                "id": msg.id,
                "from_agent_id": msg.from_agent_id,
                "content": (
                    msg.message.parts[0].text
                    if msg.message.parts and msg.message.parts[0].text
                    else None
                ),
                "task_id": msg.message.task_id,
                "context_id": msg.message.context_id,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
        "count": len(messages),
    }


# ============ Task Tools ============


@mcp.tool()
def task__create(
    ctx: Context,
    context_id: str | None = None,
    initial_message: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Create a new task.

    Args:
        context_id: Optional context ID to associate the task with.
        initial_message: Optional initial message content for the task.
        metadata: Optional metadata for the task.

    Returns:
        The created task details.
    """
    agent_id = get_agent_id_from_context(ctx)

    task = Task(
        status=TaskStatus(state=TaskState.SUBMITTED),
        metadata=metadata or {},
    )

    if context_id:
        task.context_id = context_id

    if initial_message:
        msg = Message(
            role=Role.AGENT if agent_id else Role.USER,
            parts=[Part(text=initial_message)],
            context_id=task.context_id,
            task_id=task.id,
        )
        task.history.append(msg)

    if agent_id and task.metadata is not None:
        task.metadata["created_by_agent"] = agent_id

    created_task = store.create_task(task)

    return {
        "status": "created",
        "task": {
            "id": created_task.id,
            "context_id": created_task.context_id,
            "state": created_task.status.state.value,
            "created_at": created_task.status.timestamp.isoformat(),
            "metadata": created_task.metadata,
        },
    }


@mcp.tool()
def task__get(
    ctx: Context,
    task_id: str,
    history_length: int | None = None,
) -> dict:
    """Get a task by ID.

    Args:
        task_id: The ID of the task to retrieve.
        history_length: Optional limit on number of history messages to return.

    Returns:
        The task details.
    """
    task = store.get_task(task_id)
    if not task:
        return {
            "status": "error",
            "error": f"Task with ID '{task_id}' not found",
        }

    history = task.history
    if history_length is not None:
        history = history[-history_length:]

    return {
        "status": "ok",
        "task": {
            "id": task.id,
            "context_id": task.context_id,
            "state": task.status.state.value,
            "timestamp": task.status.timestamp.isoformat(),
            "metadata": task.metadata,
            "history": [
                {
                    "message_id": msg.message_id,
                    "role": msg.role.value,
                    "content": (
                        msg.parts[0].text if msg.parts and msg.parts[0].text else None
                    ),
                }
                for msg in history
            ],
            "artifacts": [
                {
                    "artifact_id": art.artifact_id,
                    "name": art.name,
                    "description": art.description,
                }
                for art in task.artifacts
            ],
        },
    }


@mcp.tool()
def task__list(
    ctx: Context,
    context_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict:
    """List tasks with optional filtering.

    Args:
        context_id: Optional filter by context ID.
        status: Optional filter by task state (submitted, working, completed, failed, cancelled).
        limit: Maximum number of tasks to return (default: 50).

    Returns:
        List of tasks.
    """
    task_state = None
    if status:
        try:
            task_state = TaskState(status)
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid status '{status}'. Valid values: {[s.value for s in TaskState]}",
            }

    tasks, total = store.list_tasks(
        context_id=context_id,
        status=task_state,
        limit=limit,
        offset=0,
    )

    return {
        "status": "ok",
        "tasks": [
            {
                "id": task.id,
                "context_id": task.context_id,
                "state": task.status.state.value,
                "timestamp": task.status.timestamp.isoformat(),
                "metadata": task.metadata,
            }
            for task in tasks
        ],
        "total": total,
    }


@mcp.tool()
def task__update_status(
    ctx: Context,
    task_id: str,
    status: str,
    message: str | None = None,
) -> dict:
    """Update a task's status.

    Args:
        task_id: The ID of the task to update.
        status: New status (submitted, working, completed, failed, input_required).
        message: Optional status message.

    Returns:
        The updated task details.
    """
    agent_id = get_agent_id_from_context(ctx)

    task = store.get_task(task_id)
    if not task:
        return {
            "status": "error",
            "error": f"Task with ID '{task_id}' not found",
        }

    try:
        new_state = TaskState(status)
    except ValueError:
        return {
            "status": "error",
            "error": f"Invalid status '{status}'. Valid values: {[s.value for s in TaskState]}",
        }

    # Don't allow updating terminal states
    terminal_states = {
        TaskState.COMPLETED,
        TaskState.FAILED,
        TaskState.CANCELLED,
        TaskState.REJECTED,
    }
    if task.status.state in terminal_states:
        return {
            "status": "error",
            "error": f"Cannot update task in terminal state '{task.status.state.value}'",
        }

    status_message = None
    if message:
        status_message = Message(
            role=Role.AGENT if agent_id else Role.USER,
            parts=[Part(text=message)],
            task_id=task_id,
            context_id=task.context_id,
        )
        task.history.append(status_message)

    task.status = TaskStatus(
        state=new_state,
        message=status_message,
        timestamp=datetime.now(),
    )

    store.update_task(task)

    return {
        "status": "updated",
        "task": {
            "id": task.id,
            "state": task.status.state.value,
            "timestamp": task.status.timestamp.isoformat(),
        },
    }


@mcp.tool()
def task__cancel(ctx: Context, task_id: str) -> dict:
    """Cancel a task.

    Args:
        task_id: The ID of the task to cancel.

    Returns:
        The cancelled task details.
    """
    task = store.cancel_task(task_id)
    if not task:
        return {
            "status": "error",
            "error": f"Task with ID '{task_id}' not found",
        }

    return {
        "status": "cancelled",
        "task": {
            "id": task.id,
            "state": task.status.state.value,
            "timestamp": task.status.timestamp.isoformat(),
        },
    }


# ============ App Tools ============


@mcp.tool()
async def app__list(
    ctx: Context,
    healthy_only: bool = True,
    include_tools: bool = False,
) -> dict:
    """List all available Apps (scenario-based MCP services).

    Apps are automatically discovered via health checks. Only healthy apps
    that respond to their health_check_url are returned by default.

    Args:
        healthy_only: If True, only return healthy apps (default: True).
        include_tools: If True, include full tools list for each app (default: False).

    Returns a list of all registered Apps with their names, scenarios,
    descriptions, MCP endpoints, and optionally their tools.
    """
    from thronglets.app_registry import app_registry
    from thronglets.dynamic_mcp import _tools_cache, get_app_tools

    apps = app_registry.list(healthy_only=healthy_only)
    result_apps = []

    for app in apps:
        app_info = {
            "app_id": app.app_id,
            "name": app.card.name,
            "description": app.card.description,
            "scenario": app.card.scenario,
            "mcp_endpoint": app.card.mcp_endpoint,
            "health_check_url": app.card.health_check_url,
            "icon_url": app.card.icon_url,
            "tags": app.card.tags,
            "healthy": app.healthy,
            "registered_at": app.registered_at.isoformat(),
        }

        # Add tools_count from cache if available
        if app.app_id in _tools_cache:
            _, cached_tools = _tools_cache[app.app_id]
            app_info["tools_count"] = len(cached_tools)
            if include_tools:
                app_info["tools"] = cached_tools
        else:
            app_info["tools_count"] = None  # Not yet discovered
            if include_tools and app.healthy:
                # Fetch tools if requested
                try:
                    tools = await get_app_tools(app.app_id, app.card.mcp_endpoint)
                    app_info["tools_count"] = len(tools)
                    app_info["tools"] = tools
                except Exception as e:
                    logger.warning(f"Failed to get tools for app {app.app_id}: {e}")
                    app_info["tools"] = []

        result_apps.append(app_info)

    return {
        "apps": result_apps,
        "total": len(result_apps),
    }


@mcp.tool()
def app__get(ctx: Context, app_id: str) -> dict:
    """Get detailed information about a specific App.

    Args:
        app_id: The ID of the App to retrieve.

    Returns:
        The App details including MCP endpoint and health status.
    """
    from thronglets.app_registry import app_registry

    app = app_registry.get(app_id)
    if not app:
        return {
            "status": "error",
            "error": f"App with ID '{app_id}' not found",
        }

    return {
        "status": "ok",
        "app": {
            "app_id": app.app_id,
            "name": app.card.name,
            "description": app.card.description,
            "scenario": app.card.scenario,
            "mcp_endpoint": app.card.mcp_endpoint,
            "health_check_url": app.card.health_check_url,
            "icon_url": app.card.icon_url,
            "tags": app.card.tags,
            "healthy": app.healthy,
            "registered_at": app.registered_at.isoformat(),
            "last_seen_at": app.last_seen_at.isoformat(),
        },
    }


@mcp.tool()
async def app__list_tools(ctx: Context, app_id: str) -> dict:
    """List all MCP tools provided by an App.

    Connects to the App's MCP endpoint and retrieves available tools.
    Results are cached for 5 minutes.

    Args:
        app_id: The ID of the App to query.

    Returns:
        List of tools with name, description, and inputSchema.
    """
    from thronglets.app_registry import app_registry
    from thronglets.dynamic_mcp import get_app_tools

    app = app_registry.get(app_id)
    if not app:
        return {
            "status": "error",
            "error": f"App with ID '{app_id}' not found",
        }

    if not app.healthy:
        return {
            "status": "error",
            "error": f"App '{app.card.name}' is not healthy",
        }

    try:
        tools = await get_app_tools(app_id, app.card.mcp_endpoint)
        return {
            "status": "ok",
            "app_id": app_id,
            "app_name": app.card.name,
            "tools": tools,
            "tools_count": len(tools),
        }
    except Exception as e:
        logger.error(
            f"Failed to get tools from app {app_id}: {e}, endpoint: {app.card.mcp_endpoint}"
        )
        return {
            "status": "error",
            "error": f"Failed to connect to app MCP endpoint: {str(e)}",
        }


@mcp.tool()
async def app__execute(
    ctx: Context,
    app_id: str,
    tool_name: str,
    arguments: dict | None = None,
) -> dict:
    """Execute a tool on an App through ServiceBus proxy.

    ServiceBus maintains independent MCP sessions for each Agent-App pair,
    ensuring state isolation. Agent context (headers/metadata) is automatically
    passed through to the App.

    Args:
        app_id: The ID of the App to execute the tool on.
        tool_name: The name of the tool to execute.
        arguments: Arguments to pass to the tool (default: empty dict).

    Returns:
        The tool execution result.
    """
    from thronglets.app_registry import app_registry

    agent_id = get_agent_id_from_context(ctx)
    if not agent_id:
        return {
            "status": "error",
            "error": "No agent_id found in context. Make sure X-Agent-ID header is set.",
        }

    app = app_registry.get(app_id)
    if not app:
        return {
            "status": "error",
            "error": f"App with ID '{app_id}' not found",
        }

    if not app.healthy:
        return {
            "status": "error",
            "error": f"App '{app.card.name}' is not healthy",
        }

    try:
        import asyncio
        import json

        import httpx

        # Extract agent context for passing to App
        agent_context = _extract_agent_context(ctx)
        mcp_endpoint = app.card.mcp_endpoint

        async with asyncio.timeout(30.0):
            # Start with required MCP headers
            headers = {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            }

            # Pass through ALL original user headers from the request
            original_headers = agent_context.get("headers", {})
            for key, value in original_headers.items():
                # Skip headers that might conflict with MCP protocol
                if key.lower() not in [
                    "host",
                    "content-length",
                    "transfer-encoding",
                    "connection",
                ]:
                    headers[key] = value

            # Ensure X-Agent-ID is set
            if agent_context.get("agent_id"):
                headers["X-Agent-ID"] = agent_context["agent_id"]

            # Include metadata in a custom header (JSON encoded)
            original_metadata = agent_context.get("metadata", {})
            if original_metadata:
                headers["X-MCP-Metadata"] = json.dumps(original_metadata)

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
                    return {
                        "status": "error",
                        "error": f"Failed to initialize MCP session: {response.status_code}",
                    }

                session_id = response.headers.get(
                    "mcp-session-id"
                ) or response.headers.get("x-session-id")
                if not session_id:
                    return {
                        "status": "error",
                        "error": "No session ID found in MCP response",
                    }

                # Call the tool
                tool_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments or {},
                    },
                }

                session_headers = headers.copy()
                session_headers["mcp-session-id"] = session_id

                tool_response = await client.post(
                    mcp_endpoint, json=tool_request, headers=session_headers
                )

                if tool_response.status_code != 200:
                    return {
                        "status": "error",
                        "error": f"Tool execution failed: {tool_response.status_code}",
                    }

                # Parse SSE response
                tool_content = tool_response.text
                if "data: " not in tool_content:
                    return {
                        "status": "error",
                        "error": "Invalid SSE response format",
                    }

                # SSE format: "event: message\ndata: {...}\n\n"
                # Extract only the first JSON data line
                tool_json_data = None
                for line in tool_content.split("\n"):
                    line = line.strip()
                    if line.startswith("data: "):
                        tool_json_data = line[6:]  # Remove "data: " prefix
                        break

                if not tool_json_data:
                    return {
                        "status": "error",
                        "error": "No data found in SSE response",
                    }

                tool_result = json.loads(tool_json_data)

                # Check for JSON-RPC error
                if "error" in tool_result:
                    return {
                        "status": "error",
                        "error": tool_result["error"].get("message", "Unknown error"),
                    }

                result_data = tool_result.get("result", {})
                content_items = []

                # Process content from result
                for content in result_data.get("content", []):
                    if content.get("type") == "text":
                        content_items.append(
                            {"type": "text", "text": content.get("text", "")}
                        )
                    elif content.get("type") == "image":
                        content_items.append(
                            {"type": "image", "data": content.get("data", "")}
                        )
                    else:
                        content_items.append(
                            {
                                "type": content.get("type", "unknown"),
                                "raw": str(content),
                            }
                        )

                return {
                    "status": "ok",
                    "app_id": app_id,
                    "app_name": app.card.name,
                    "tool_name": tool_name,
                    "result": content_items,
                    "is_error": result_data.get("isError", False),
                }

    except Exception as e:
        logger.error(f"Failed to execute tool {tool_name} on app {app_id}: {e}")
        return {
            "status": "error",
            "error": f"Failed to execute tool: {str(e)}",
        }


def _extract_agent_context(ctx: Context) -> dict:
    """Extract agent context from MCP request for passing to Apps.

    Extracts ALL user headers and metadata from the current request context
    to be passed through to App MCP calls.

    Args:
        ctx: The MCP context.

    Returns:
        Dict containing:
        - agent_id: The agent ID from X-Agent-ID header
        - headers: All HTTP headers from the original request
        - metadata: Any metadata from the MCP request context
    """
    context: dict = {
        "agent_id": None,
        "headers": {},
        "metadata": {},
    }

    # Extract agent_id
    agent_id = get_agent_id_from_context(ctx)
    if agent_id:
        context["agent_id"] = agent_id

    # Extract ALL HTTP headers
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers()
        if headers:
            # Pass through ALL headers (convert to dict if needed)
            context["headers"] = dict(headers) if hasattr(headers, "items") else headers
    except Exception:
        pass

    # Extract metadata from MCP request context
    try:
        if ctx.request_context and ctx.request_context.meta:
            meta = ctx.request_context.meta
            if hasattr(meta, "items"):
                context["metadata"] = dict(meta)
            elif hasattr(meta, "__dict__"):
                context["metadata"] = {
                    k: v for k, v in meta.__dict__.items() if not k.startswith("_")
                }
    except Exception:
        pass

    return context


def run_mcp_server() -> None:
    """Run the MCP server in stdio mode."""
    mcp.run()


if __name__ == "__main__":
    run_mcp_server()
