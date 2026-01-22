"""Bus Client for connecting to Thronglets ServiceBus."""

from __future__ import annotations

import asyncio
import threading

import httpx

from thronglets.models import AgentCard, RegisteredAgent


class BusClientError(Exception):
    """Exception raised by BusClient operations."""

    pass


class BusClient:
    """Client for connecting to Thronglets ServiceBus.

    This client handles agent registration and health checks via HTTP API.

    Usage:
        with Bus(url="http://localhost:8000", agent_card=my_card) as client:
            # client is registered
            print(client.agent_id)

    Or async:
        async with Bus.connect_async(url="...", agent_card=my_card) as client:
            print(client.agent_id)
    """

    def __init__(
        self,
        url: str,
        agent_card: AgentCard | dict,
        health_check_interval: float = 30.0,
    ) -> None:
        """Initialize the client.

        Args:
            url: The base URL of the ServiceBus (e.g., http://localhost:8000).
            agent_card: The AgentCard for this agent.
            health_check_interval: Interval for health checks in seconds.
        """
        self.url = url.rstrip("/")
        self._agent_card = (
            agent_card if isinstance(agent_card, AgentCard) else AgentCard(**agent_card)
        )
        self.health_check_interval = health_check_interval

        self._registered_agent: RegisteredAgent | None = None
        self._http_client: httpx.Client | None = None
        self._async_http_client: httpx.AsyncClient | None = None

        self._health_check_task: asyncio.Task | None = None
        self._health_check_thread: threading.Thread | None = None
        self._stop_health_check = threading.Event()

    @property
    def agent_id(self) -> str | None:
        """Get the registered agent ID."""
        return self._registered_agent.agent_id if self._registered_agent else None

    @property
    def agent_card(self) -> AgentCard:
        """Get the agent card."""
        return self._agent_card

    @property
    def mcp_address(self) -> str:
        """Get the MCP address."""
        return f"{self.url}/bus/mcp"

    @property
    def registered_agent(self) -> RegisteredAgent | None:
        """Get the registered agent info."""
        return self._registered_agent

    # ============ Sync Context Manager ============

    def __enter__(self) -> "BusClient":
        """Enter the context manager (sync)."""
        self._http_client = httpx.Client(timeout=30.0)
        self._register_agent_sync()
        self._start_health_check_thread()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager (sync)."""
        self._stop_health_check.set()
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5.0)
        self._unregister_agent_sync()
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    # ============ Async Context Manager ============

    async def __aenter__(self) -> "BusClient":
        """Enter the context manager (async)."""
        self._async_http_client = httpx.AsyncClient(timeout=30.0)
        await self._register_agent_async()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager (async)."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        await self._unregister_agent_async()
        if self._async_http_client:
            await self._async_http_client.aclose()
            self._async_http_client = None

    # ============ Agent Registration ============

    def _register_agent_sync(self) -> None:
        """Register the agent with the ServiceBus (sync)."""
        if not self._http_client:
            raise BusClientError("HTTP client not initialized")

        response = self._http_client.post(
            f"{self.url}/agents",
            json=self._agent_card.model_dump(),
        )
        if response.status_code != 200:
            raise BusClientError(f"Failed to register agent: {response.text}")

        data = response.json()
        self._registered_agent = RegisteredAgent(**data)

    async def _register_agent_async(self) -> None:
        """Register the agent with the ServiceBus (async)."""
        if not self._async_http_client:
            raise BusClientError("HTTP client not initialized")

        response = await self._async_http_client.post(
            f"{self.url}/agents",
            json=self._agent_card.model_dump(),
        )
        if response.status_code != 200:
            raise BusClientError(f"Failed to register agent: {response.text}")

        data = response.json()
        self._registered_agent = RegisteredAgent(**data)

    def _unregister_agent_sync(self) -> None:
        """Unregister the agent from the ServiceBus (sync)."""
        if not self._http_client or not self._registered_agent:
            return

        try:
            self._http_client.delete(
                f"{self.url}/agents/{self._registered_agent.agent_id}"
            )
        except Exception:
            pass  # Best effort
        self._registered_agent = None

    async def _unregister_agent_async(self) -> None:
        """Unregister the agent from the ServiceBus (async)."""
        if not self._async_http_client or not self._registered_agent:
            return

        try:
            await self._async_http_client.delete(
                f"{self.url}/agents/{self._registered_agent.agent_id}"
            )
        except Exception:
            pass  # Best effort
        self._registered_agent = None

    # ============ Health Check ============

    def _start_health_check_thread(self) -> None:
        """Start a background thread for health checks."""
        self._stop_health_check.clear()
        self._health_check_thread = threading.Thread(
            target=self._health_check_thread_func, daemon=True
        )
        self._health_check_thread.start()

    def _health_check_thread_func(self) -> None:
        """Health check thread function."""
        while not self._stop_health_check.wait(self.health_check_interval):
            try:
                self._register_agent_sync()
                print(
                    f"🔄 Health check: Registered agent {self._registered_agent.agent_id}"
                )
            except Exception:
                print(
                    f"❌ Health check failed for agent {self._registered_agent.agent_id}"
                )
                pass

    async def _health_check_loop(self) -> None:
        """Async health check loop."""
        while True:
            await asyncio.sleep(self.health_check_interval)
            try:
                await self._register_agent_async()
                print(
                    f"🔄 Health check: Registered agent {self._registered_agent.agent_id}"
                )
            except asyncio.CancelledError:
                break
            except Exception:
                print(
                    f"❌ Health check failed for agent {self._registered_agent.agent_id}"
                )
                pass


# Convenience alias
Bus = BusClient
