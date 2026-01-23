"""HTTP API service using FastAPI."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.logger import logger
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from thronglets.app_registry import app_registry
from thronglets.auth import AUTH_ENABLED, get_auth_config
from thronglets.dynamic_mcp import get_app_tools
from thronglets.mcp_server import mcp
from thronglets.models import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    AppCard,
    Message,
    RegisteredAgent,
    RegisteredApp,
    Task,
    TaskState,
    TaskStatus,
)
from thronglets.store import store

# Environment variables for configuration
THRONGLETS_HOST = os.getenv("THRONGLETS_HOST", "localhost")
THRONGLETS_PORT = os.getenv("THRONGLETS_PORT", "8000")
THRONGLETS_MCP_PATH = os.getenv("THRONGLETS_MCP_PATH", "/bus/mcp")

bus_mcp = mcp.http_app(transport="streamable-http", path="/mcp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Start health checks for apps
    app_registry.start_health_checks()

    async with bus_mcp.lifespan(app):
        yield

    # Cleanup on shutdown
    app_registry.stop_health_checks()


app = FastAPI(
    title="Thronglets ServiceBus",
    description="Multi-Agent ServiceBus based on A2A protocol",
    version="0.1.0",
    lifespan=lifespan,
    debug=True,
)
app.mount("/bus", bus_mcp)
logger.setLevel(logging.DEBUG)


stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)


# Response models
class AgentListResponse(BaseModel):
    agents: list[RegisteredAgent]
    total: int


class TaskListResponse(BaseModel):
    tasks: list[Task]
    total: int
    page_size: int
    next_page_token: str


class CreateTaskRequest(BaseModel):
    context_id: str | None = None
    initial_message: Message | None = None
    metadata: dict | None = None


class AppListResponse(BaseModel):
    apps: list[RegisteredApp]
    total: int


class ToolInfo(BaseModel):
    name: str
    description: str
    inputSchema: dict


class AppToolsResponse(BaseModel):
    tools: list[ToolInfo]


# ServiceBus's own AgentCard
SERVICE_BUS_CARD = AgentCard(
    name="Thronglets ServiceBus",
    description="Multi-Agent ServiceBus for agent registration, discovery, and communication",
    version="0.1.0",
    protocol_versions=["1.0"],
    supported_interfaces=[
        AgentInterface(
            url="http://localhost:8000",
            protocol_binding="HTTP+JSON",
        )
    ],
    capabilities=AgentCapabilities(
        streaming=False,
        push_notifications=False,
    ),
    skills=[
        AgentSkill(
            id="agent-registry",
            name="Agent Registry",
            description="Register and discover agents",
            tags=["registry", "discovery"],
        ),
        AgentSkill(
            id="task-management",
            name="Task Management",
            description="Create and manage tasks",
            tags=["task", "workflow"],
        ),
        AgentSkill(
            id="message-routing",
            name="Message Routing",
            description="Route messages between agents",
            tags=["message", "communication"],
        ),
    ],
    default_input_modes=["application/json"],
    default_output_modes=["application/json"],
)

# MCP Tools metadata
MCP_TOOLS = [
    {
        "name": "agent__list",
        "description": "List all registered agents in the ServiceBus",
        "category": "Agent",
    },
    {
        "name": "agent__whoami",
        "description": "Get the current agent's information",
        "category": "Agent",
    },
    {
        "name": "message__send",
        "description": "Send a message to another agent",
        "category": "Message",
    },
    {
        "name": "message__receive",
        "description": "Receive messages sent to this agent",
        "category": "Message",
    },
    {
        "name": "task__create",
        "description": "Create a new task",
        "category": "Task",
    },
    {
        "name": "task__get",
        "description": "Get a task by ID",
        "category": "Task",
    },
    {
        "name": "task__list",
        "description": "List tasks with optional filtering",
        "category": "Task",
    },
    {
        "name": "task__update_status",
        "description": "Update a task's status",
        "category": "Task",
    },
    {
        "name": "task__cancel",
        "description": "Cancel a task",
        "category": "Task",
    },
    {
        "name": "app__list",
        "description": "List all available Apps (scenario-based MCP services)",
        "category": "App",
    },
    {
        "name": "app__get",
        "description": "Get detailed information about a specific App",
        "category": "App",
    },
]


# System info endpoint
@app.get("/system/info")
async def get_system_info() -> dict:
    """Get system information including MCP tools and health status."""
    base_url = f"http://{THRONGLETS_HOST}:{THRONGLETS_PORT}"
    mcp_url = f"{base_url}{THRONGLETS_MCP_PATH}"

    agents = store.list_agents()
    apps = app_registry.list(healthy_only=False)
    healthy_apps = [a for a in apps if a.healthy]

    return {
        "name": "Thronglets ServiceBus",
        "version": "0.1.0",
        "description": "Multi-Agent ServiceBus for agent registration, discovery, and communication based on A2A protocol",
        "mcp": {
            "endpoint": mcp_url,
            "transport": "streamable-http",
            "tools": MCP_TOOLS,
            "auth": get_auth_config(),
        },
        "health": {
            "status": "healthy",
            "agents_count": len(agents),
            "apps_count": len(apps),
            "healthy_apps_count": len(healthy_apps),
        },
        "endpoints": {
            "base_url": base_url,
            "mcp_url": mcp_url,
            "agent_card": f"{base_url}/.well-known/agent",
        },
    }


# Well-known endpoint
@app.get("/.well-known/agent", response_model=AgentCard)
async def get_agent_card() -> AgentCard:
    """Get the ServiceBus's AgentCard."""
    return SERVICE_BUS_CARD


# Agent endpoints
@app.post("/agents", response_model=RegisteredAgent)
async def register_agent(card: AgentCard) -> RegisteredAgent:
    """Register a new agent or renew existing agent registration."""
    # Check if agent with same name already exists (for renewal)
    existing_agents = store.list_agents()
    for existing_agent in existing_agents:
        if (
            existing_agent.card.name == card.name
            and existing_agent.card.version == card.version
        ):
            # This is a renewal, update last_seen_at and keep same agent_id
            existing_agent.last_seen_at = datetime.now()
            store.register_agent(existing_agent)  # This will update TTL
            return existing_agent
    # This is a new registration
    agent = RegisteredAgent(card=card)
    return store.register_agent(agent)


@app.get("/agents", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """List all registered agents."""
    agents = store.list_agents()
    return AgentListResponse(agents=agents, total=len(agents))


@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str) -> dict:
    """Delete an agent."""
    if not store.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "deleted", "agent_id": agent_id}


# App endpoints
@app.post("/apps", response_model=RegisteredApp)
async def register_app(card: AppCard) -> RegisteredApp:
    """Register a new app or renew existing app registration.

    The app must provide a health_check_url for health monitoring.
    Unhealthy apps will be automatically removed.
    """
    return app_registry.register(card)


@app.get("/apps", response_model=AppListResponse)
async def list_apps(healthy_only: bool = Query(True)) -> AppListResponse:
    """List all registered apps.

    Args:
        healthy_only: If true, only return healthy apps (default: true).
    """
    apps = app_registry.list(healthy_only=healthy_only)
    return AppListResponse(apps=apps, total=len(apps))


@app.get("/apps/{app_id}", response_model=RegisteredApp)
async def get_app(app_id: str) -> RegisteredApp:
    """Get an app by ID."""
    app_instance = app_registry.get(app_id)
    if not app_instance:
        raise HTTPException(status_code=404, detail="App not found")
    return app_instance


@app.put("/apps/{app_id}", response_model=RegisteredApp)
async def update_app(app_id: str, card: AppCard) -> RegisteredApp:
    """Update an existing app."""
    app_instance = app_registry.get(app_id)
    if not app_instance:
        raise HTTPException(status_code=404, detail="App not found")
    return app_registry.update(app_id, card)


@app.delete("/apps/{app_id}")
async def delete_app(app_id: str) -> dict:
    """Delete an app."""
    if not app_registry.delete(app_id):
        raise HTTPException(status_code=404, detail="App not found")
    return {"status": "deleted", "app_id": app_id}


@app.get("/apps/{app_id}/tools", response_model=AppToolsResponse)
async def get_app_tools_endpoint(app_id: str) -> AppToolsResponse:
    """Get the list of MCP tools provided by an app.

    Connects to the app's MCP endpoint and retrieves available tools.
    Results are cached for 5 minutes.
    """
    app_instance = app_registry.get(app_id)
    if not app_instance:
        raise HTTPException(status_code=404, detail="App not found")

    if not app_instance.healthy:
        raise HTTPException(status_code=503, detail="App is not healthy")

    try:
        tools = await get_app_tools(app_id, app_instance.card.mcp_endpoint)
        return AppToolsResponse(tools=[ToolInfo(**tool) for tool in tools])
    except Exception as e:
        logger.error(
            f"Failed to get tools from app {app_id}: {e}, endpoint: {app_instance.card.mcp_endpoint}"
        )
        raise HTTPException(
            status_code=503, detail=f"Failed to connect to app MCP endpoint: {str(e)}"
        )


# Task endpoints
@app.post("/tasks", response_model=Task)
async def create_task(request: CreateTaskRequest) -> Task:
    """Create a new task."""
    task = Task(
        status=TaskStatus(state=TaskState.SUBMITTED),
        metadata=request.metadata,
    )
    if request.context_id:
        task.context_id = request.context_id
    if request.initial_message:
        task.history.append(request.initial_message)

    return store.create_task(task)


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    context_id: str | None = Query(None),
    status: TaskState | None = Query(None),
    page_size: int = Query(50, ge=1, le=100),
    page_token: str = Query(""),
) -> TaskListResponse:
    """List tasks with optional filtering."""
    offset = int(page_token) if page_token else 0
    tasks, total = store.list_tasks(
        context_id=context_id,
        status=status,
        limit=page_size,
        offset=offset,
    )

    next_offset = offset + page_size
    next_token = str(next_offset) if next_offset < total else ""

    return TaskListResponse(
        tasks=tasks,
        total=total,
        page_size=page_size,
        next_page_token=next_token,
    )


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    history_length: int | None = Query(None),
) -> Task:
    """Get a task by ID."""
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if history_length is not None:
        task = task.model_copy()
        task.history = task.history[-history_length:]

    return task


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> dict:
    """Delete a task."""
    if not store.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted", "task_id": task_id}


@app.post("/tasks/{task_id}/cancel", response_model=Task)
async def cancel_task(task_id: str) -> Task:
    """Cancel a task."""
    task = store.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# Frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# Mount static assets if the dist directory exists
if FRONTEND_DIR.exists():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the frontend dashboard."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(
        status_code=404,
        detail="Frontend not found. Run 'npm run build' in the frontend directory.",
    )


def run_http_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the HTTP server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_http_server()
