"""Active cloud backend used by tools, CLI, and Streamlit.

Always resolves through ``get_cloud_provider()`` so ``CLOUD_BACKEND=simulator|aws``
takes effect without changing call sites.
"""
from __future__ import annotations

from typing import Any

from strandops.simulator.provider import get_cloud_provider


class _CloudProxy:
    """Attribute proxy onto the configured CloudProvider singleton."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_cloud_provider(), name)

    def __repr__(self) -> str:
        return f"<CloudProxy -> {get_cloud_provider()!r}>"


cloud = _CloudProxy()


def list_known_services() -> list[str]:
    """Return service names for the active backend (simulator or AWS)."""
    backend = get_cloud_provider()
    configs = getattr(backend, "service_configs", None)
    if isinstance(configs, dict) and configs:
        return list(configs.keys())
    known = getattr(backend, "known_services", None)
    if isinstance(known, list) and known:
        return list(known)
    return list(backend.get_topology().keys())
