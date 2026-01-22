"""In-memory storage implementation."""

from collections import defaultdict
from datetime import datetime

from thronglets.models import (
    InternalMessage,
    RegisteredAgent,
    RegisteredApp,
    Task,
    TaskState,
)
from thronglets.storage.base import Storage, StorageConfig


class MemoryStorageConfig(StorageConfig):
    """Configuration for in-memory storage."""

    type: str = "memory"


class MemoryStorage(Storage):
    """In-memory storage implementation.

    This storage keeps all data in memory and is lost when the process exits.
    Suitable for development and testing.
    """

    def __init__(self, config: MemoryStorageConfig | None = None) -> None:
        """Initialize in-memory storage."""
        super().__init__(config or MemoryStorageConfig())
        self._agents: dict[str, RegisteredAgent] = {}
        self._tasks: dict[str, Task] = {}
        self._messages: dict[str, list[InternalMessage]] = defaultdict(list)
        self._apps: dict[str, RegisteredApp] = {}
        self._connected = False

    # ============ Lifecycle ============

    def connect(self) -> None:
        """No-op for memory storage."""
        self._connected = True

    def disconnect(self) -> None:
        """No-op for memory storage."""
        self._connected = False

    def is_connected(self) -> bool:
        """Memory storage is always 'connected'."""
        return self._connected

    # ============ Agent Operations ============

    def register_agent(self, agent: RegisteredAgent) -> RegisteredAgent:
        """Register a new agent."""
        self._agents[agent.agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> RegisteredAgent | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[RegisteredAgent]:
        """List all registered agents."""
        return list(self._agents.values())

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    # ============ Task Operations ============

    def create_task(self, task: Task) -> Task:
        """Create a new task."""
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        context_id: str | None = None,
        status: TaskState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """List tasks with optional filtering."""
        tasks = list(self._tasks.values())

        if context_id:
            tasks = [t for t in tasks if t.context_id == context_id]

        if status:
            tasks = [t for t in tasks if t.status.state == status]

        total = len(tasks)
        tasks = tasks[offset : offset + limit]
        return tasks, total

    def update_task(self, task: Task) -> Task:
        """Update an existing task."""
        self._tasks[task.id] = task
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        terminal_states = {
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELLED,
            TaskState.REJECTED,
        }
        if task.status.state in terminal_states:
            return task

        task.status.state = TaskState.CANCELLED
        task.status.timestamp = datetime.now()
        return task

    # ============ Message Operations ============

    def send_message(self, message: InternalMessage) -> InternalMessage:
        """Send a message to an agent."""
        self._messages[message.to_agent_id].append(message)
        return message

    def receive_messages(
        self,
        agent_id: str,
        mark_as_read: bool = True,
        limit: int = 100,
    ) -> list[InternalMessage]:
        """Receive messages for an agent."""
        messages = self._messages.get(agent_id, [])
        unread = [m for m in messages if not m.read][:limit]

        if mark_as_read:
            for m in unread:
                m.read = True

        return unread

    def get_all_messages(self, agent_id: str) -> list[InternalMessage]:
        """Get all messages for an agent."""
        return self._messages.get(agent_id, [])

    # ============ App Operations ============

    def register_app(self, app: RegisteredApp) -> RegisteredApp:
        """Register a new app."""
        self._apps[app.app_id] = app
        return app

    def get_app(self, app_id: str) -> RegisteredApp | None:
        """Get an app by ID."""
        return self._apps.get(app_id)

    def list_apps(self, healthy_only: bool = True) -> list[RegisteredApp]:
        """List all registered apps."""
        apps = list(self._apps.values())
        if healthy_only:
            apps = [a for a in apps if a.healthy]
        return apps

    def update_app(self, app: RegisteredApp) -> RegisteredApp:
        """Update an existing app."""
        self._apps[app.app_id] = app
        return app

    def delete_app(self, app_id: str) -> bool:
        """Delete an app."""
        if app_id in self._apps:
            del self._apps[app_id]
            return True
        return False
