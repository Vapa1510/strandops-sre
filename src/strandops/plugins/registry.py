"""Action Registry for SRE Remediation Plugins.

Central registry that manages all registered remediation primitives, validates
input parameters, and dispatches execution.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from strandops.plugins.base import RemediationPlugin
from strandops.plugins.actions import (
    QuarantineMessagesPlugin,
    RestartServicePlugin,
    RollbackConfigPlugin,
    ScaleServicePlugin,
    DrainTrafficPlugin,
    FlushCachePlugin,
    TripCircuitBreakerPlugin,
    RerouteTrafficPlugin,
)


class ActionRegistry:
    """Registry maintaining active remediation plugins."""

    def __init__(self) -> None:
        self._plugins: Dict[str, RemediationPlugin] = {}
        self._register_default_plugins()

    def _register_default_plugins(self) -> None:
        """Register the standard SRE runbook primitives."""
        self.register(QuarantineMessagesPlugin())
        self.register(RestartServicePlugin())
        self.register(RollbackConfigPlugin())
        self.register(ScaleServicePlugin())
        self.register(DrainTrafficPlugin())
        self.register(FlushCachePlugin())
        self.register(TripCircuitBreakerPlugin())
        self.register(RerouteTrafficPlugin())

    def register(self, plugin: RemediationPlugin) -> None:
        """Register a new remediation plugin."""
        self._plugins[plugin.action_name.lower()] = plugin

    def get(self, action_name: str) -> Optional[RemediationPlugin]:
        """Retrieve a registered plugin by name (case-insensitive, normalized)."""
        key = action_name.strip().lower().replace("-", "_")
        return self._plugins.get(key)

    def list_actions(self) -> List[Dict[str, Any]]:
        """Return metadata for all registered actions."""
        return [
            {
                "name": p.action_name,
                "description": p.description,
                "risk_level": p.risk_level,
                "allowed_services": p.allowed_services,
            }
            for p in self._plugins.values()
        ]

    def evaluate_safety(self, cloud: Any, action_name: str, target: str) -> Dict[str, Any]:
        """Evaluate the safety and blast-radius of a proposed action."""
        plugin = self.get(action_name)
        if not plugin:
            return {
                "target": target,
                "action": action_name,
                "risk_level": "HIGH",
                "safe_to_proceed": False,
                "direct_dependents": [],
                "dependent_count": 0,
                "safety_rationale": [f"Unknown action '{action_name}'. Not found in SRE Runbook Registry."],
            }
        return plugin.evaluate_blast_radius(cloud, target)

    def execute(self, cloud: Any, action_name: str, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and execute a registered remediation plugin."""
        plugin = self.get(action_name)
        if not plugin:
            return {
                "status": "error",
                "message": f"Unsupported action '{action_name}'. Registered: {list(self._plugins.keys())}",
            }
        return plugin.execute(cloud, target, parameters)


# Global singleton registry
registry = ActionRegistry()
