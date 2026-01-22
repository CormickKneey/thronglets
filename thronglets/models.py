"""Data models based on A2A protocol."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def generate_uuid() -> str:
    return str(uuid4())


class TaskState(str, Enum):
    """Defines the possible lifecycle states of a Task."""

    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INPUT_REQUIRED = "input_required"
    REJECTED = "rejected"
    AUTH_REQUIRED = "auth_required"


class Role(str, Enum):
    """Defines the sender of a message."""

    USER = "user"
    AGENT = "agent"


class FilePart(BaseModel):
    """File content representation."""

    file_with_uri: str | None = None
    file_with_bytes: bytes | None = None
    media_type: str | None = None
    name: str | None = None


class DataPart(BaseModel):
    """Structured data blob."""

    data: dict[str, Any]


class Part(BaseModel):
    """Container for a section of communication content."""

    text: str | None = None
    file: FilePart | None = None
    data: DataPart | None = None
    metadata: dict[str, Any] | None = None


class Message(BaseModel):
    """One unit of communication between client and server."""

    message_id: str = Field(default_factory=generate_uuid)
    context_id: str | None = None
    task_id: str | None = None
    role: Role
    parts: list[Part]
    metadata: dict[str, Any] | None = None
    extensions: list[str] | None = None
    reference_task_ids: list[str] | None = None


class Artifact(BaseModel):
    """Task output representation."""

    artifact_id: str = Field(default_factory=generate_uuid)
    name: str | None = None
    description: str | None = None
    parts: list[Part]
    metadata: dict[str, Any] | None = None
    extensions: list[str] | None = None


class TaskStatus(BaseModel):
    """Container for the status of a task."""

    state: TaskState
    message: Message | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class Task(BaseModel):
    """Core unit of action for A2A."""

    id: str = Field(default_factory=generate_uuid)
    context_id: str = Field(default_factory=generate_uuid)
    status: TaskStatus
    artifacts: list[Artifact] = Field(default_factory=list)
    history: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class AgentInterface(BaseModel):
    """Combination of a target URL and transport protocol."""

    url: str
    protocol_binding: str
    tenant: str | None = None


class AgentProvider(BaseModel):
    """Service provider of an agent."""

    url: str
    organization: str


class AgentExtension(BaseModel):
    """Protocol extension supported by an Agent."""

    uri: str
    description: str | None = None
    required: bool = False
    params: dict[str, Any] | None = None


class AgentCapabilities(BaseModel):
    """Optional capabilities supported by an agent."""

    streaming: bool | None = None
    push_notifications: bool | None = None
    extensions: list[AgentExtension] | None = None
    state_transition_history: bool | None = None
    extended_agent_card: bool | None = None


class AgentSkill(BaseModel):
    """Distinct capability or function that an agent can perform."""

    id: str
    name: str
    description: str
    tags: list[str]
    examples: list[str] | None = None
    input_modes: list[str] | None = None
    output_modes: list[str] | None = None


class AgentCard(BaseModel):
    """Self-describing manifest for an agent."""

    name: str
    description: str
    version: str
    protocol_versions: list[str] = Field(default=["1.0"])
    supported_interfaces: list[AgentInterface]
    provider: AgentProvider | None = None
    documentation_url: str | None = None
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    skills: list[AgentSkill]
    default_input_modes: list[str] = Field(default=["text/plain"])
    default_output_modes: list[str] = Field(default=["text/plain"])
    icon_url: str | None = None


class RegisteredAgent(BaseModel):
    """Agent registered in the ServiceBus with additional metadata."""

    agent_id: str = Field(default_factory=generate_uuid)
    card: AgentCard
    registered_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    message: Message
    to_agent_id: str | None = None
    blocking: bool = False
    history_length: int | None = None


class InternalMessage(BaseModel):
    """Internal message storage with routing information."""

    id: str = Field(default_factory=generate_uuid)
    from_agent_id: str | None = None
    to_agent_id: str
    message: Message
    created_at: datetime = Field(default_factory=datetime.now)
    read: bool = False


class AppCard(BaseModel):
    """Self-describing manifest for a scenario-based MCP service (App)."""

    name: str
    description: str
    scenario: str
    mcp_endpoint: str
    health_check_url: str
    icon_url: str | None = None
    tags: list[str] | None = None


class RegisteredApp(BaseModel):
    """App registered in the ServiceBus with additional metadata."""

    app_id: str = Field(default_factory=generate_uuid)
    card: AppCard
    registered_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    healthy: bool = True
