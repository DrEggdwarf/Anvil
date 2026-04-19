"""Bridge registry — dynamic registration and lookup of bridge types."""

from __future__ import annotations

from backend.app.bridges.base import BaseBridge


class BridgeRegistry:
    """Singleton registry for all available bridge types."""

    def __init__(self) -> None:
        self._bridges: dict[str, type[BaseBridge]] = {}

    def register(self, bridge_type: str, bridge_class: type[BaseBridge]) -> None:
        """Register a bridge class for a given type name."""
        self._bridges[bridge_type] = bridge_class

    def get(self, bridge_type: str) -> type[BaseBridge] | None:
        """Lookup a bridge class by type name. Returns None if not found."""
        return self._bridges.get(bridge_type)

    def list_types(self) -> list[str]:
        """Return all registered bridge type names."""
        return list(self._bridges.keys())

    def __contains__(self, bridge_type: str) -> bool:
        return bridge_type in self._bridges

    def __len__(self) -> int:
        return len(self._bridges)


# Global singleton — bridges register themselves at import time
bridge_registry = BridgeRegistry()
