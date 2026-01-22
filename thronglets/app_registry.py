"""App Registry with health check based discovery.

This module provides App registration with optional persistence via Storage.
Apps are discovered and removed based on health check status.
"""

import asyncio
import logging
from datetime import datetime

import httpx

from thronglets.models import AppCard, RegisteredApp

logger = logging.getLogger(__name__)


class AppRegistry:
    """App registry with health check based lifecycle management.

    Apps register themselves and provide a health_check_url.
    The registry periodically checks health endpoints and marks unhealthy apps.
    Data is persisted via the Storage backend.
    """

    def __init__(
        self,
        health_check_interval: float = 30.0,
        health_check_timeout: float = 5.0,
        unhealthy_threshold: int = 3,
    ) -> None:
        """Initialize the App registry.

        Args:
            health_check_interval: Seconds between health checks.
            health_check_timeout: Timeout for each health check request.
            unhealthy_threshold: Number of consecutive failures before marking app unhealthy.
        """
        self._failure_counts: dict[str, int] = {}
        self._health_check_interval = health_check_interval
        self._health_check_timeout = health_check_timeout
        self._unhealthy_threshold = unhealthy_threshold
        self._health_check_task: asyncio.Task | None = None
        self._running = False

    @property
    def _storage(self):
        """Get storage backend lazily to avoid circular imports."""
        from thronglets.store import store

        return store.storage

    def register(self, card: AppCard) -> RegisteredApp:
        """Register a new app or update existing one.

        Args:
            card: The app's card with health_check_url.

        Returns:
            The registered app.
        """
        # Check if app with same name already exists
        existing = self._storage.find_app_by_name(card.name)
        if existing:
            existing.card = card
            existing.last_seen_at = datetime.now()
            existing.healthy = True
            self._failure_counts[existing.app_id] = 0
            self._storage.update_app(existing)
            logger.info(f"App renewed: {card.name} (id={existing.app_id})")
            return existing

        app = RegisteredApp(card=card)
        self._storage.register_app(app)
        self._failure_counts[app.app_id] = 0
        logger.info(f"App registered: {card.name} (id={app.app_id})")
        return app

    def get(self, app_id: str) -> RegisteredApp | None:
        """Get an app by ID."""
        return self._storage.get_app(app_id)

    def list(self, healthy_only: bool = True) -> list[RegisteredApp]:
        """List all registered apps.

        Args:
            healthy_only: If True, only return healthy apps.
        """
        return self._storage.list_apps(healthy_only=healthy_only)

    def delete(self, app_id: str) -> bool:
        """Delete an app."""
        app = self._storage.get_app(app_id)
        if app:
            self._failure_counts.pop(app_id, None)
            result = self._storage.delete_app(app_id)
            if result:
                logger.info(f"App deleted: {app.card.name} (id={app_id})")
            return result
        return False

    def update(self, app_id: str, card: AppCard) -> RegisteredApp | None:
        """Update an existing app's card.

        Args:
            app_id: The app's ID.
            card: The new app card.

        Returns:
            The updated app, or None if not found.
        """
        app = self._storage.get_app(app_id)
        if not app:
            return None
        app.card = card
        app.last_seen_at = datetime.now()
        self._failure_counts[app_id] = 0
        self._storage.update_app(app)
        logger.info(f"App updated: {card.name} (id={app_id})")
        return app

    def find_by_name(self, name: str) -> RegisteredApp | None:
        """Find an app by name."""
        return self._storage.find_app_by_name(name)

    async def _check_health(self, app: RegisteredApp) -> bool:
        """Check the health of a single app.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=self._health_check_timeout) as client:
                response = await client.get(app.card.health_check_url)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed for {app.card.name}: {e}")
            return False

    async def _health_check_loop(self) -> None:
        """Background task that periodically checks app health."""
        while self._running:
            apps_to_check = self._storage.list_apps(healthy_only=False)

            for app in apps_to_check:
                # Re-fetch to check if still exists
                current_app = self._storage.get_app(app.app_id)
                if not current_app:
                    continue

                healthy = await self._check_health(current_app)

                if healthy:
                    if not current_app.healthy:
                        current_app.healthy = True
                        self._storage.update_app(current_app)
                    current_app.last_seen_at = datetime.now()
                    self._failure_counts[current_app.app_id] = 0
                else:
                    self._failure_counts[current_app.app_id] = (
                        self._failure_counts.get(current_app.app_id, 0) + 1
                    )

                    if current_app.healthy:
                        current_app.healthy = False
                        self._storage.update_app(current_app)

                    if (
                        self._failure_counts[current_app.app_id]
                        >= self._unhealthy_threshold
                    ):
                        logger.warning(
                            f"App marked unhealthy: {current_app.card.name} "
                            f"(id={current_app.app_id}, failures={self._failure_counts[current_app.app_id]})"
                        )

            await asyncio.sleep(self._health_check_interval)

    def start_health_checks(self) -> None:
        """Start the background health check task."""
        if self._running:
            return
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Health check service started")

    def stop_health_checks(self) -> None:
        """Stop the background health check task."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None
        logger.info("Health check service stopped")


# Global registry instance
app_registry = AppRegistry()
