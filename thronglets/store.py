"""Store module - provides global storage access for the ServiceBus.

This module maintains a global storage instance that can be configured
via environment variables or programmatically.
"""

import os
from typing import TYPE_CHECKING

from thronglets.storage import (
    MemoryStorage,
    MemoryStorageConfig,
    RedisStorage,
    RedisStorageConfig,
    Storage,
    StorageConfig,
    create_storage,
)

if TYPE_CHECKING:
    from thronglets.models import (
        InternalMessage,
        RegisteredAgent,
        Task,
        TaskState,
    )


class Store:
    """Store wrapper that delegates to a Storage backend.

    This class maintains backward compatibility with the original Store API
    while allowing different storage backends to be used.
    """

    def __init__(self, storage: Storage | None = None) -> None:
        """Initialize store with a storage backend.

        Args:
            storage: Storage backend to use. If None, creates from environment.
        """
        self._storage = storage or self._create_storage_from_env()
        if not self._storage.is_connected():
            self._storage.connect()

    @staticmethod
    def _create_storage_from_env() -> Storage:
        """Create storage from environment variables.

        Environment variables:
            THRONGLETS_STORAGE_TYPE: "memory" or "redis" (default: "memory")
            THRONGLETS_REDIS_URL: Redis URL (default: "redis://localhost:6379")
            THRONGLETS_REDIS_DB: Redis database number (default: 0)
            THRONGLETS_REDIS_PREFIX: Key prefix (default: "thronglets:")
        """
        storage_type = os.environ.get("THRONGLETS_STORAGE_TYPE", "memory").lower()

        if storage_type == "redis":
            config = RedisStorageConfig(
                url=os.environ.get("THRONGLETS_REDIS_URL", "redis://localhost:6379"),
                db=int(os.environ.get("THRONGLETS_REDIS_DB", "0")),
                key_prefix=os.environ.get("THRONGLETS_REDIS_PREFIX", "thronglets:"),
            )
            return RedisStorage(config)
        else:
            return MemoryStorage(MemoryStorageConfig())

    @property
    def storage(self) -> Storage:
        """Get the underlying storage backend."""
        return self._storage

    def configure(self, config: StorageConfig) -> None:
        """Reconfigure the store with a new storage backend.

        Args:
            config: New storage configuration.
        """
        # Disconnect old storage
        if self._storage.is_connected():
            self._storage.disconnect()

        # Create and connect new storage
        self._storage = create_storage(config)
        self._storage.connect()

    # ============ Agent Operations ============

    def register_agent(self, agent: "RegisteredAgent") -> "RegisteredAgent":
        """Register a new agent."""
        return self._storage.register_agent(agent)

    def get_agent(self, agent_id: str) -> "RegisteredAgent | None":
        """Get an agent by ID."""
        return self._storage.get_agent(agent_id)

    def list_agents(self) -> list["RegisteredAgent"]:
        """List all registered agents."""
        return self._storage.list_agents()

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        return self._storage.delete_agent(agent_id)

    def find_agent_by_name(self, name: str) -> "RegisteredAgent | None":
        """Find an agent by name."""
        return self._storage.find_agent_by_name(name)

    def touch_agent(self, agent_id: str) -> "RegisteredAgent | None":
        """Update agent's last_seen_at timestamp."""
        return self._storage.touch_agent(agent_id)

    def cleanup_expired_agents(self, max_age_seconds: float) -> list[str]:
        """Remove agents that haven't been seen within the threshold."""
        return self._storage.cleanup_expired_agents(max_age_seconds)

    # ============ Task Operations ============

    def create_task(self, task: "Task") -> "Task":
        """Create a new task."""
        return self._storage.create_task(task)

    def get_task(self, task_id: str) -> "Task | None":
        """Get a task by ID."""
        return self._storage.get_task(task_id)

    def list_tasks(
        self,
        context_id: str | None = None,
        status: "TaskState | None" = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list["Task"], int]:
        """List tasks with optional filtering."""
        return self._storage.list_tasks(
            context_id=context_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def update_task(self, task: "Task") -> "Task":
        """Update an existing task."""
        return self._storage.update_task(task)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        return self._storage.delete_task(task_id)

    def cancel_task(self, task_id: str) -> "Task | None":
        """Cancel a task."""
        return self._storage.cancel_task(task_id)

    # ============ Message Operations ============

    def send_message(self, message: "InternalMessage") -> "InternalMessage":
        """Send a message to an agent."""
        return self._storage.send_message(message)

    def receive_messages(
        self,
        agent_id: str,
        mark_as_read: bool = True,
        limit: int = 100,
    ) -> list["InternalMessage"]:
        """Receive messages for an agent."""
        return self._storage.receive_messages(
            agent_id=agent_id,
            mark_as_read=mark_as_read,
            limit=limit,
        )

    def get_all_messages(self, agent_id: str) -> list["InternalMessage"]:
        """Get all messages for an agent (including read)."""
        return self._storage.get_all_messages(agent_id)


# Global store instance
store = Store()
