# Thronglets Developer Guide

This document provides detailed architecture design, data models, and development instructions for Thronglets.

## Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Thronglets ServiceBus                     │
├─────────────────────────────┬───────────────────────────────┤
│     HTTP API (FastAPI)      │    MCP Server (FastMCP)       │
│     /agents, /apps, /tasks  │    /bus/mcp (streamable-http) │
├─────────────────────────────┼───────────────────────────────┤
│  Agent Management           │  Agent Tools                  │
│  - POST /agents             │  - agent__list                │
│  - GET  /agents             │  - agent__whoami              │
│  - DELETE /agents/{id}      │                               │
├─────────────────────────────┼───────────────────────────────┤
│  App Management             │  App Tools                    │
│  - POST /apps               │  - app__list                  │
│  - GET  /apps               │  - app__get                   │
│  - GET  /apps/{id}          │  - app__list_tools            │
│  - GET  /apps/{id}/tools    │  - app__execute               │
│  - DELETE /apps/{id}        │                               │
├─────────────────────────────┼───────────────────────────────┤
│  Task Management            │  Message/Task Tools           │
│  - POST /tasks              │  - message__send              │
│  - GET  /tasks              │  - message__receive           │
│  - GET  /tasks/{id}         │  - task__create/get/list      │
│  - DELETE /tasks/{id}       │  - task__update_status        │
│  - POST /tasks/{id}/cancel  │  - task__cancel               │
└─────────────────────────────┴───────────────────────────────┘
                    │                       │
        ┌───────────┴───────────┐           │
        ▼                       ▼           ▼
┌───────────────┐      ┌───────────────┐  ┌───────────────┐
│ Storage Layer │      │ App Registry  │  │ Session Mgr   │
│ Memory/Redis  │      │ (In-Memory)   │  │ Agent-App MCP │
└───────────────┘      └───────────────┘  └───────────────┘
```

**Key Design Points:**
- HTTP API and MCP Server run in the same HTTP service
- MCP Server is mounted at `/bus/mcp` using `streamable-http` transport
- Agents register via HTTP API and maintain online status through periodic heartbeats (every minute, timeout removal)
- Apps register via HTTP API and must provide `health_check_url`; system performs periodic health checks
- MCP tools automatically identify caller identity via `X-Agent-ID` header
- Dynamic MCP enables agents to discover and execute App tools through proxy

## Project Structure

```
thronglets/
├── pyproject.toml          # Project configuration and dependencies
├── main.py                 # Main entry point
├── README.md               # Project overview
├── AGENT.md                # Developer guide (this document)
└── thronglets/
    ├── __init__.py         # Package exports
    ├── models.py           # Data models
    ├── store.py            # Storage facade
    ├── http_api.py         # HTTP API (FastAPI)
    ├── mcp_server.py       # MCP Server (FastMCP)
    ├── client.py           # BusClient
    ├── app_registry.py     # App registry (health checks)
    ├── dynamic_mcp.py      # Dynamic MCP session manager
    ├── main.py             # CLI entry point
    └── storage/
        ├── __init__.py     # Storage module exports
        ├── base.py         # Abstract base class
        ├── memory.py       # Memory storage
        └── redis.py        # Redis storage
```

## Data Models

### AgentCard

Agent's self-description manifest:

```python
class AgentCard:
    name: str                           # Agent name
    description: str                    # Agent description
    version: str                        # Agent version
    protocol_versions: list[str]        # Supported protocol versions
    supported_interfaces: list[AgentInterface]  # Supported interfaces
    capabilities: AgentCapabilities     # Capability set
    skills: list[AgentSkill]           # Skill list
```

### AppCard

App (scenario-based MCP service) self-description manifest:

```python
class AppCard:
    name: str               # App name
    description: str        # App description
    scenario: str           # Scenario (e.g., "finance", "game-dev")
    mcp_endpoint: str       # MCP service endpoint
    health_check_url: str   # Health check endpoint (required)
    icon_url: str | None    # Icon URL
    tags: list[str] | None  # Tags
```

### RegisteredApp

Registered App record:

```python
class RegisteredApp:
    app_id: str             # App ID (UUID)
    card: AppCard           # App card
    registered_at: datetime # Registration time
    last_seen_at: datetime  # Last health check time
    healthy: bool           # Health status
```

### Task

Task execution unit:

```python
class Task:
    id: str                    # Task ID (UUID)
    context_id: str           # Context ID
    status: TaskStatus        # Task status
    artifacts: list[Artifact] # Output artifacts
    history: list[Message]    # Interaction history

class TaskState(Enum):
    SUBMITTED = "submitted"       # Submitted
    WORKING = "working"           # In progress
    COMPLETED = "completed"       # Completed (terminal)
    FAILED = "failed"             # Failed (terminal)
    CANCELLED = "cancelled"       # Cancelled (terminal)
    INPUT_REQUIRED = "input_required"
    REJECTED = "rejected"         # Rejected (terminal)
    AUTH_REQUIRED = "auth_required"
```

### Message

Inter-agent communication message:

```python
class Message:
    message_id: str           # Message ID (UUID)
    context_id: str | None    # Context ID
    task_id: str | None       # Associated task ID
    role: Role                # Sender role (USER/AGENT)
    parts: list[Part]         # Message content
```

## HTTP API Reference

### Agent Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agents` | Register agent; resubmitting same name+version renews |
| GET | `/agents` | List all agents |
| DELETE | `/agents/{id}` | Unregister agent |
| GET | `/.well-known/agent` | Get ServiceBus's own AgentCard |

### App Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/apps` | Register App; must provide health_check_url |
| GET | `/apps` | List all Apps; supports `healthy_only` parameter |
| GET | `/apps/{id}` | Get App details |
| GET | `/apps/{id}/tools` | Get App's MCP tool list |
| DELETE | `/apps/{id}` | Unregister App |

### Task Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Create task |
| GET | `/tasks` | List tasks; supports context_id/status filtering |
| GET | `/tasks/{id}` | Get task details |
| DELETE | `/tasks/{id}` | Delete task |
| POST | `/tasks/{id}/cancel` | Cancel task |

## MCP Tools Reference

MCP service automatically identifies current Agent identity via `X-Agent-ID` header.

### Agent Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `agent__list` | - | List all registered agents |
| `agent__whoami` | - | Get current agent info |

### App Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `app__list` | healthy_only: bool, include_tools: bool, key_words: list[str] | List all Apps; defaults to healthy only |
| `app__get` | app_id: str | Get App details including MCP endpoint |
| `app__list_tools` | app_id: str | List tools provided by an App |
| `app__execute` | app_id: str, tool_name: str, arguments: dict | Execute an App tool through proxy |

### Message Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `message__send` | to_agent_id, content, task_id?, context_id? | Send message |
| `message__receive` | mark_as_read?, limit? | Receive messages |

### Task Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `task__create` | context_id?, initial_message?, metadata? | Create task |
| `task__get` | task_id, history_length? | Get task details |
| `task__list` | context_id?, status?, limit? | List tasks |
| `task__update_status` | task_id, status, message? | Update task status |
| `task__cancel` | task_id | Cancel task |

## App Registry Mechanism

Apps use health check mechanism instead of persistent storage to simplify operations:

```python
class AppRegistry:
    def __init__(
        self,
        health_check_interval: float = 30.0,  # Check interval
        health_check_timeout: float = 5.0,    # Timeout
        unhealthy_threshold: int = 3,         # Failure threshold
    )
```

**Lifecycle:**
1. App calls `POST /apps` to register; must provide `health_check_url`
2. System periodically calls `health_check_url` to check App health
3. After N consecutive health check failures, App is automatically removed from registry
4. App can call `POST /apps` again to renew (update last_seen_at)

## Dynamic MCP

Dynamic MCP enables agents to discover and execute App tools at runtime through ServiceBus proxy.

### Session Management Architecture

```
┌─────────────┐     ┌─────────────────────────────────────┐     ┌─────────────┐
│   Agent A   │────▶│         Thronglets ServiceBus       │────▶│   App 1     │
└─────────────┘     │                                     │     └─────────────┘
                    │  ┌─────────────────────────────┐    │
┌─────────────┐     │  │   AgentAppSessionManager    │    │     ┌─────────────┐
│   Agent B   │────▶│  │                             │    │────▶│   App 2     │
└─────────────┘     │  │  Sessions:                  │    │     └─────────────┘
                    │  │  (A, App1) -> ClientSession │    │
                    │  │  (A, App2) -> ClientSession │    │
                    │  │  (B, App1) -> ClientSession │    │
                    │  └─────────────────────────────┘    │
                    └─────────────────────────────────────┘
```

### Context Inheritance Flow

```
Agent Request                    ServiceBus                         App
    │                               │                                │
    │  app__execute(app1, tool, {}) │                                │
    │  Headers: X-Agent-ID=agent-a  │                                │
    │  ──────────────────────────▶  │                                │
    │                               │                                │
    │                               │  1. Extract agent context      │
    │                               │  2. Get/Create session         │
    │                               │  3. Call tool with context     │
    │                               │  ──────────────────────────▶   │
    │                               │                                │
    │                               │  ◀──────────────────────────   │
    │                               │     Tool result                │
    │  ◀──────────────────────────  │                                │
    │     Result                    │                                │
```

### Session Configuration

```python
class AgentAppSessionManager:
    session_ttl: float = 1800.0      # Session TTL (30 minutes)
    max_sessions_per_agent: int = 10 # Max sessions per agent
```

## Storage Layer

Supports pluggable storage backends for Agent, Task, and Message persistence.

### Configuration

**Environment Variables:**

```bash
# Memory storage (default)
export THRONGLETS_STORAGE_TYPE=memory

# Redis storage
export THRONGLETS_STORAGE_TYPE=redis
export THRONGLETS_REDIS_URL=redis://localhost:6379
export THRONGLETS_REDIS_DB=0
export THRONGLETS_REDIS_PREFIX=thronglets:
```

**Code Configuration:**

```python
from thronglets import RedisStorageConfig
from thronglets.store import store

config = RedisStorageConfig(
    url="redis://localhost:6379",
    db=0,
    key_prefix="thronglets:",
    agent_ttl=60,           # Agent expiration (seconds)
    task_ttl=86400 * 7,     # Task retention: 7 days
    message_ttl=86400 * 3,  # Message retention: 3 days
)
store.configure(config)
```

### Redis Data Structures

- **Agents**: `{prefix}agent:{id}` (Hash) + `{prefix}agents` (Set)
- **Tasks**: `{prefix}task:{id}` (Hash) + multi-dimensional indexes
- **Messages**: `{prefix}message:{id}` (Hash) + queues

## Starting the Service

```bash
# Install dependencies
uv sync

# Start service (HTTP API + MCP Server)
uv run python main.py --port 8000

# With Redis storage
THRONGLETS_STORAGE_TYPE=redis THRONGLETS_REDIS_URL=redis://localhost:6379 \
    uv run python main.py --port 8000

# MCP stdio mode only (for Claude Desktop)
uv run python main.py --mcp-stdio
```

## Using BusClient

```python
from thronglets import BusClient, AgentCard, AgentInterface, AgentSkill

my_card = AgentCard(
    name="MyAgent",
    description="A sample agent",
    version="1.0.0",
    supported_interfaces=[
        AgentInterface(url="http://localhost:9000", protocol_binding="HTTP+JSON")
    ],
    skills=[
        AgentSkill(id="echo", name="Echo", description="Echoes input", tags=["utility"])
    ],
)

# Synchronous usage
with BusClient(url="http://localhost:8000", agent_card=my_card) as client:
    print(f"Agent ID: {client.agent_id}")
    # Auto-register, heartbeat maintenance, unregister on exit

# Asynchronous usage
async with BusClient(url="http://localhost:8000", agent_card=my_card) as client:
    ...
```

## Register App Example

```bash
curl -X POST http://localhost:8000/apps \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Stock Trading App",
    "description": "Stock trading analysis tools",
    "scenario": "finance",
    "mcp_endpoint": "http://stock-app:8001/mcp",
    "health_check_url": "http://stock-app:8001/health",
    "tags": ["finance", "trading"]
  }'
```

## Using Dynamic MCP

```bash
# List tools from an App
curl http://localhost:8000/apps/{app_id}/tools

# Or via MCP tool
app__list_tools(app_id="xxx")
# -> [{"name": "get_stock_price", "description": "...", "inputSchema": {...}}]

# Execute an App tool
app__execute(
    app_id="xxx",
    tool_name="get_stock_price",
    arguments={"symbol": "AAPL"}
)
```

## Tech Stack

- **Web Framework**: FastAPI
- **MCP Framework**: FastMCP
- **Package Management**: uv
- **Data Storage**: Memory / Redis
- **Health Checks**: httpx (async)
- **MCP Client**: mcp Python SDK
