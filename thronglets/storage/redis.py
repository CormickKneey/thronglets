"""Redis storage implementation."""

import json
from datetime import datetime
from typing import Any

import redis

from thronglets.models import (
    InternalMessage,
    RegisteredAgent,
    RegisteredApp,
    Task,
    TaskState,
)
from thronglets.storage.base import Storage, StorageConfig


class RedisStorageConfig(StorageConfig):
    """Configuration for Redis storage."""

    type: str = "redis"
    url: str = "redis://localhost:6379"
    db: int = 0
    key_prefix: str = "thronglets:"
    # TTL settings (in seconds)
    agent_ttl: int = 60  # 1 minute
    task_ttl: int = 86400 * 7  # 7 days
    message_ttl: int = 86400 * 3  # 3 days
    app_ttl: int = 0  # No TTL for apps (persistent)
    # Connection settings
    decode_responses: bool = True
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0


class RedisStorage(Storage):
    """Redis storage implementation.

    Data structures used:
    - Agents:
      - Hash: `{prefix}agent:{id}` - agent data
      - Set: `{prefix}agents` - all agent IDs for listing

    - Tasks:
      - Hash: `{prefix}task:{id}` - task data
      - Set: `{prefix}tasks` - all task IDs
      - Set: `{prefix}tasks:context:{context_id}` - task IDs by context
      - Set: `{prefix}tasks:status:{status}` - task IDs by status
      - Sorted Set: `{prefix}tasks:by_time` - task IDs sorted by timestamp

    - Messages:
      - List: `{prefix}messages:{agent_id}` - message queue (FIFO)
      - Hash: `{prefix}message:{id}` - message data
      - Set: `{prefix}messages:{agent_id}:unread` - unread message IDs

    - Apps:
      - Hash: `{prefix}app:{id}` - app data
      - Set: `{prefix}apps` - all app IDs for listing
    """

    def __init__(self, config: RedisStorageConfig | None = None) -> None:
        """Initialize Redis storage."""
        super().__init__(config or RedisStorageConfig())
        self.config: RedisStorageConfig = self.config  # type hint
        self._client: redis.Redis | None = None

    @property
    def prefix(self) -> str:
        """Get the key prefix."""
        return self.config.key_prefix

    def _key(self, *parts: str) -> str:
        """Build a Redis key with prefix."""
        return self.prefix + ":".join(parts)

    # ============ Lifecycle ============

    def connect(self) -> None:
        """Connect to Redis."""
        self._client = redis.from_url(
            self.config.url,
            db=self.config.db,
            decode_responses=self.config.decode_responses,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
        )
        # Test connection
        self._client.ping()

    def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            self._client.close()
            self._client = None

    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except redis.ConnectionError:
            return False

    @property
    def client(self) -> redis.Redis:
        """Get Redis client, raising if not connected."""
        if not self._client:
            raise RuntimeError("Redis storage not connected. Call connect() first.")
        return self._client

    # ============ Serialization ============

    def _serialize(self, obj: Any) -> str:
        """Serialize an object to JSON string."""
        if hasattr(obj, "model_dump"):
            return json.dumps(obj.model_dump(), default=str)
        return json.dumps(obj, default=str)

    def _deserialize_agent(self, data: str | None) -> RegisteredAgent | None:
        """Deserialize agent from JSON."""
        if not data:
            return None
        return RegisteredAgent.model_validate_json(data)

    def _deserialize_task(self, data: str | None) -> Task | None:
        """Deserialize task from JSON."""
        if not data:
            return None
        return Task.model_validate_json(data)

    def _deserialize_message(self, data: str | None) -> InternalMessage | None:
        """Deserialize message from JSON."""
        if not data:
            return None
        return InternalMessage.model_validate_json(data)

    def _deserialize_app(self, data: str | None) -> RegisteredApp | None:
        """Deserialize app from JSON."""
        if not data:
            return None
        return RegisteredApp.model_validate_json(data)

    # ============ Agent Operations ============

    def register_agent(self, agent: RegisteredAgent) -> RegisteredAgent:
        """Register a new agent or renew existing agent registration."""
        agent_key = self._key("agent", agent.agent_id)
        agents_set_key = self._key("agents")

        # Check if agent already exists
        existing_data = self.client.get(agent_key)
        if existing_data:
            # This is a renewal - update last_seen_at and TTL only
            agent.last_seen_at = datetime.now()

        pipe = self.client.pipeline()
        pipe.set(agent_key, self._serialize(agent))
        pipe.sadd(agents_set_key, agent.agent_id)

        if self.config.agent_ttl:
            pipe.expire(agent_key, self.config.agent_ttl)

        pipe.execute()
        return agent

    def get_agent(self, agent_id: str) -> RegisteredAgent | None:
        """Get an agent by ID."""
        agent_key = self._key("agent", agent_id)
        data = self.client.get(agent_key)
        return self._deserialize_agent(data)

    def list_agents(self) -> list[RegisteredAgent]:
        """List all registered agents."""
        agents_set_key = self._key("agents")
        agent_ids = self.client.smembers(agents_set_key)

        if not agent_ids:
            return []

        # Use pipeline to fetch all agents efficiently
        pipe = self.client.pipeline()
        for agent_id in agent_ids:
            pipe.get(self._key("agent", agent_id))

        results = pipe.execute()
        agents = []
        for data in results:
            agent = self._deserialize_agent(data)
            if agent:
                agents.append(agent)

        return agents

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        agent_key = self._key("agent", agent_id)
        agents_set_key = self._key("agents")

        pipe = self.client.pipeline()
        pipe.delete(agent_key)
        pipe.srem(agents_set_key, agent_id)
        results = pipe.execute()

        return results[0] > 0  # True if key was deleted

    # ============ Task Operations ============

    def _add_task_to_indices(
        self, pipe: redis.client.Pipeline, task: Task, timestamp: float
    ) -> None:
        """Add task to all indices."""
        tasks_set_key = self._key("tasks")
        context_set_key = self._key("tasks", "context", task.context_id)
        status_set_key = self._key("tasks", "status", task.status.state.value)
        time_sorted_key = self._key("tasks", "by_time")

        pipe.sadd(tasks_set_key, task.id)
        pipe.sadd(context_set_key, task.id)
        pipe.sadd(status_set_key, task.id)
        pipe.zadd(time_sorted_key, {task.id: timestamp})

    def _remove_task_from_indices(
        self, pipe: redis.client.Pipeline, task: Task
    ) -> None:
        """Remove task from all indices."""
        tasks_set_key = self._key("tasks")
        context_set_key = self._key("tasks", "context", task.context_id)
        time_sorted_key = self._key("tasks", "by_time")

        pipe.srem(tasks_set_key, task.id)
        pipe.srem(context_set_key, task.id)
        pipe.zrem(time_sorted_key, task.id)

        # Remove from all status sets
        for state in TaskState:
            status_set_key = self._key("tasks", "status", state.value)
            pipe.srem(status_set_key, task.id)

    def create_task(self, task: Task) -> Task:
        """Create a new task."""
        task_key = self._key("task", task.id)
        timestamp = task.status.timestamp.timestamp()

        pipe = self.client.pipeline()
        pipe.set(task_key, self._serialize(task))
        self._add_task_to_indices(pipe, task, timestamp)

        if self.config.task_ttl:
            pipe.expire(task_key, self.config.task_ttl)

        pipe.execute()
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        task_key = self._key("task", task_id)
        data = self.client.get(task_key)
        return self._deserialize_task(data)

    def list_tasks(
        self,
        context_id: str | None = None,
        status: TaskState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """List tasks with optional filtering."""
        # Determine which set to use for filtering
        if context_id and status:
            # Intersection of context and status sets
            context_set_key = self._key("tasks", "context", context_id)
            status_set_key = self._key("tasks", "status", status.value)
            task_ids = self.client.sinter(context_set_key, status_set_key)
        elif context_id:
            context_set_key = self._key("tasks", "context", context_id)
            task_ids = self.client.smembers(context_set_key)
        elif status:
            status_set_key = self._key("tasks", "status", status.value)
            task_ids = self.client.smembers(status_set_key)
        else:
            tasks_set_key = self._key("tasks")
            task_ids = self.client.smembers(tasks_set_key)

        if not task_ids:
            return [], 0

        total = len(task_ids)
        task_ids = list(task_ids)[offset : offset + limit]

        if not task_ids:
            return [], total

        # Fetch tasks
        pipe = self.client.pipeline()
        for task_id in task_ids:
            pipe.get(self._key("task", task_id))

        results = pipe.execute()
        tasks = []
        for data in results:
            task = self._deserialize_task(data)
            if task:
                tasks.append(task)

        return tasks, total

    def update_task(self, task: Task) -> Task:
        """Update an existing task."""
        task_key = self._key("task", task.id)

        # Get old task to update indices
        old_data = self.client.get(task_key)
        old_task = self._deserialize_task(old_data)

        pipe = self.client.pipeline()

        # Remove from old status index if status changed
        if old_task and old_task.status.state != task.status.state:
            old_status_key = self._key("tasks", "status", old_task.status.state.value)
            new_status_key = self._key("tasks", "status", task.status.state.value)
            pipe.srem(old_status_key, task.id)
            pipe.sadd(new_status_key, task.id)

        # Update task data
        pipe.set(task_key, self._serialize(task))

        # Update timestamp in sorted set
        time_sorted_key = self._key("tasks", "by_time")
        pipe.zadd(time_sorted_key, {task.id: task.status.timestamp.timestamp()})

        if self.config.task_ttl:
            pipe.expire(task_key, self.config.task_ttl)

        pipe.execute()
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        task_key = self._key("task", task_id)

        # Get task first to remove from indices
        data = self.client.get(task_key)
        task = self._deserialize_task(data)

        if not task:
            return False

        pipe = self.client.pipeline()
        pipe.delete(task_key)
        self._remove_task_from_indices(pipe, task)
        pipe.execute()

        return True

    def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a task."""
        task = self.get_task(task_id)
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

        # Update status
        old_status = task.status.state
        task.status.state = TaskState.CANCELLED
        task.status.timestamp = datetime.now()

        # Update in Redis
        task_key = self._key("task", task.id)
        old_status_key = self._key("tasks", "status", old_status.value)
        new_status_key = self._key("tasks", "status", TaskState.CANCELLED.value)
        time_sorted_key = self._key("tasks", "by_time")

        pipe = self.client.pipeline()
        pipe.set(task_key, self._serialize(task))
        pipe.srem(old_status_key, task.id)
        pipe.sadd(new_status_key, task.id)
        pipe.zadd(time_sorted_key, {task.id: task.status.timestamp.timestamp()})

        if self.config.task_ttl:
            pipe.expire(task_key, self.config.task_ttl)

        pipe.execute()
        return task

    # ============ Message Operations ============

    def send_message(self, message: InternalMessage) -> InternalMessage:
        """Send a message to an agent.

        Uses a List for the message queue (FIFO) and a Hash for message data.
        Also maintains a Set of unread message IDs per agent.
        """
        message_key = self._key("message", message.id)
        queue_key = self._key("messages", message.to_agent_id)
        unread_key = self._key("messages", message.to_agent_id, "unread")

        pipe = self.client.pipeline()

        # Store message data
        pipe.set(message_key, self._serialize(message))

        # Add to agent's message queue (push to right for FIFO)
        pipe.rpush(queue_key, message.id)

        # Add to unread set
        pipe.sadd(unread_key, message.id)

        # Set TTL
        if self.config.message_ttl:
            pipe.expire(message_key, self.config.message_ttl)
            pipe.expire(queue_key, self.config.message_ttl)
            pipe.expire(unread_key, self.config.message_ttl)

        pipe.execute()
        return message

    def receive_messages(
        self,
        agent_id: str,
        mark_as_read: bool = True,
        limit: int = 100,
    ) -> list[InternalMessage]:
        """Receive messages for an agent."""
        unread_key = self._key("messages", agent_id, "unread")

        # Get unread message IDs
        unread_ids = self.client.smembers(unread_key)
        if not unread_ids:
            return []

        unread_ids = list(unread_ids)[:limit]

        # Fetch message data
        pipe = self.client.pipeline()
        for msg_id in unread_ids:
            pipe.get(self._key("message", msg_id))

        results = pipe.execute()
        messages = []
        for i, data in enumerate(results):
            msg = self._deserialize_message(data)
            if msg:
                messages.append(msg)

        # Mark as read
        if mark_as_read and messages:
            pipe = self.client.pipeline()
            for msg in messages:
                msg.read = True
                # Update message in storage
                pipe.set(self._key("message", msg.id), self._serialize(msg))
                # Remove from unread set
                pipe.srem(unread_key, msg.id)
            pipe.execute()

        return messages

    def get_all_messages(self, agent_id: str) -> list[InternalMessage]:
        """Get all messages for an agent (including read)."""
        queue_key = self._key("messages", agent_id)

        # Get all message IDs from queue
        message_ids = self.client.lrange(queue_key, 0, -1)
        if not message_ids:
            return []

        # Fetch message data
        pipe = self.client.pipeline()
        for msg_id in message_ids:
            pipe.get(self._key("message", msg_id))

        results = pipe.execute()
        messages = []
        for data in results:
            msg = self._deserialize_message(data)
            if msg:
                messages.append(msg)

        return messages

    # ============ App Operations ============

    def register_app(self, app: RegisteredApp) -> RegisteredApp:
        """Register a new app."""
        app_key = self._key("app", app.app_id)
        apps_set_key = self._key("apps")

        pipe = self.client.pipeline()
        pipe.set(app_key, self._serialize(app))
        pipe.sadd(apps_set_key, app.app_id)

        if self.config.app_ttl:
            pipe.expire(app_key, self.config.app_ttl)

        pipe.execute()
        return app

    def get_app(self, app_id: str) -> RegisteredApp | None:
        """Get an app by ID."""
        app_key = self._key("app", app_id)
        data = self.client.get(app_key)
        return self._deserialize_app(data)

    def list_apps(self, healthy_only: bool = True) -> list[RegisteredApp]:
        """List all registered apps."""
        apps_set_key = self._key("apps")
        app_ids = self.client.smembers(apps_set_key)

        if not app_ids:
            return []

        # Use pipeline to fetch all apps efficiently
        pipe = self.client.pipeline()
        for app_id in app_ids:
            pipe.get(self._key("app", app_id))

        results = pipe.execute()
        apps = []
        for data in results:
            app = self._deserialize_app(data)
            if app:
                if healthy_only and not app.healthy:
                    continue
                apps.append(app)

        return apps

    def update_app(self, app: RegisteredApp) -> RegisteredApp:
        """Update an existing app."""
        app_key = self._key("app", app.app_id)

        pipe = self.client.pipeline()
        pipe.set(app_key, self._serialize(app))

        if self.config.app_ttl:
            pipe.expire(app_key, self.config.app_ttl)

        pipe.execute()
        return app

    def delete_app(self, app_id: str) -> bool:
        """Delete an app."""
        app_key = self._key("app", app_id)
        apps_set_key = self._key("apps")

        pipe = self.client.pipeline()
        pipe.delete(app_key)
        pipe.srem(apps_set_key, app_id)
        results = pipe.execute()

        return results[0] > 0  # True if key was deleted
