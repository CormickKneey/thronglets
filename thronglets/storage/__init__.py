"""Storage layer for Thronglets ServiceBus."""

from thronglets.storage.base import Storage, StorageConfig
from thronglets.storage.memory import MemoryStorage, MemoryStorageConfig
from thronglets.storage.redis import RedisStorage, RedisStorageConfig

__all__ = [
    "Storage",
    "StorageConfig",
    "MemoryStorage",
    "MemoryStorageConfig",
    "RedisStorage",
    "RedisStorageConfig",
    "create_storage",
]


def create_storage(config: StorageConfig) -> Storage:
    """Create a storage instance from configuration.

    Args:
        config: Storage configuration object.

    Returns:
        Storage instance.

    Example:
        >>> config = MemoryStorageConfig()
        >>> storage = create_storage(config)

        >>> config = RedisStorageConfig(url="redis://localhost:6379")
        >>> storage = create_storage(config)
    """
    if isinstance(config, MemoryStorageConfig):
        return MemoryStorage(config)
    elif isinstance(config, RedisStorageConfig):
        return RedisStorage(config)
    else:
        raise ValueError(f"Unknown storage config type: {type(config)}")
