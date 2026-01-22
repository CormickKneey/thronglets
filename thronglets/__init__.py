"""Thronglets - Multi-Agent ServiceBus based on A2A protocol."""

from thronglets.client import Bus, BusClient
from thronglets.models import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Message,
    Part,
    RegisteredAgent,
    Role,
    Task,
    TaskState,
    TaskStatus,
)
from thronglets.storage import (
    MemoryStorage,
    MemoryStorageConfig,
    RedisStorage,
    RedisStorageConfig,
    Storage,
    StorageConfig,
    create_storage,
)

__version__ = "0.1.0"

__all__ = [
    # Client
    "Bus",
    "BusClient",
    # Models
    "AgentCard",
    "AgentCapabilities",
    "AgentInterface",
    "AgentSkill",
    "Message",
    "Part",
    "RegisteredAgent",
    "Role",
    "Task",
    "TaskState",
    "TaskStatus",
    # Storage
    "Storage",
    "StorageConfig",
    "MemoryStorage",
    "MemoryStorageConfig",
    "RedisStorage",
    "RedisStorageConfig",
    "create_storage",
]
