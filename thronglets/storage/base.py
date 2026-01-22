"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from thronglets.models import (
    InternalMessage,
    RegisteredAgent,
    RegisteredApp,
    Task,
    TaskState,
)


class StorageConfig(BaseModel):
    """Base configuration for storage backends."""

    type: str = "memory"


class Storage(ABC):
    """Abstract base class for storage backends.

    All storage implementations must inherit from this class and implement
    the required methods for agents, tasks, and messages.
    """

    def __init__(self, config: StorageConfig) -> None:
        """Initialize storage with configuration."""
        self.config = config

    # ============ Lifecycle ============

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the storage backend."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the storage backend."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if storage is connected."""
        pass

    # ============ Agent Operations ============

    @abstractmethod
    def register_agent(self, agent: RegisteredAgent) -> RegisteredAgent:
        """Register a new agent.

        Args:
            agent: The agent to register.

        Returns:
            The registered agent.
        """
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> RegisteredAgent | None:
        """Get an agent by ID.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            The agent if found, None otherwise.
        """
        pass

    @abstractmethod
    def list_agents(self) -> list[RegisteredAgent]:
        """List all registered agents.

        Returns:
            List of all registered agents.
        """
        pass

    @abstractmethod
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        pass

    def find_agent_by_name(self, name: str) -> RegisteredAgent | None:
        """Find an agent by name.

        Args:
            name: The agent's name.

        Returns:
            The agent if found, None otherwise.
        """
        for agent in self.list_agents():
            if agent.card.name == name:
                return agent
        return None

    # ============ Task Operations ============

    @abstractmethod
    def create_task(self, task: Task) -> Task:
        """Create a new task.

        Args:
            task: The task to create.

        Returns:
            The created task.
        """
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: The task's unique identifier.

        Returns:
            The task if found, None otherwise.
        """
        pass

    @abstractmethod
    def list_tasks(
        self,
        context_id: str | None = None,
        status: TaskState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """List tasks with optional filtering.

        Args:
            context_id: Filter by context ID.
            status: Filter by task state.
            limit: Maximum number of tasks to return.
            offset: Number of tasks to skip.

        Returns:
            Tuple of (tasks list, total count).
        """
        pass

    @abstractmethod
    def update_task(self, task: Task) -> Task:
        """Update an existing task.

        Args:
            task: The task with updated data.

        Returns:
            The updated task.
        """
        pass

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: The task's unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        pass

    @abstractmethod
    def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a task.

        Args:
            task_id: The task's unique identifier.

        Returns:
            The cancelled task if found, None otherwise.
        """
        pass

    # ============ Message Operations ============

    @abstractmethod
    def send_message(self, message: InternalMessage) -> InternalMessage:
        """Send a message to an agent.

        Args:
            message: The message to send.

        Returns:
            The sent message.
        """
        pass

    @abstractmethod
    def receive_messages(
        self,
        agent_id: str,
        mark_as_read: bool = True,
        limit: int = 100,
    ) -> list[InternalMessage]:
        """Receive messages for an agent.

        Args:
            agent_id: The receiving agent's ID.
            mark_as_read: Whether to mark messages as read.
            limit: Maximum number of messages to return.

        Returns:
            List of unread messages.
        """
        pass

    @abstractmethod
    def get_all_messages(self, agent_id: str) -> list[InternalMessage]:
        """Get all messages for an agent (including read).

        Args:
            agent_id: The agent's ID.

        Returns:
            List of all messages.
        """
        pass

    # ============ App Operations ============

    @abstractmethod
    def register_app(self, app: RegisteredApp) -> RegisteredApp:
        """Register a new app.

        Args:
            app: The app to register.

        Returns:
            The registered app.
        """
        pass

    @abstractmethod
    def get_app(self, app_id: str) -> RegisteredApp | None:
        """Get an app by ID.

        Args:
            app_id: The app's unique identifier.

        Returns:
            The app if found, None otherwise.
        """
        pass

    @abstractmethod
    def list_apps(self, healthy_only: bool = True) -> list[RegisteredApp]:
        """List all registered apps.

        Args:
            healthy_only: If True, only return healthy apps.

        Returns:
            List of registered apps.
        """
        pass

    @abstractmethod
    def update_app(self, app: RegisteredApp) -> RegisteredApp:
        """Update an existing app.

        Args:
            app: The app with updated data.

        Returns:
            The updated app.
        """
        pass

    @abstractmethod
    def delete_app(self, app_id: str) -> bool:
        """Delete an app.

        Args:
            app_id: The app's unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        pass

    def find_app_by_name(self, name: str) -> RegisteredApp | None:
        """Find an app by name.

        Args:
            name: The app's name.

        Returns:
            The app if found, None otherwise.
        """
        for app in self.list_apps(healthy_only=False):
            if app.card.name == name:
                return app
        return None
