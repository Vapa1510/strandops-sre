"""Base classes for the Pluggable SRE Runbook Registry.

Allows engineering teams to safely define new self-healing actions as typed
Pydantic plugins with custom guardrails and declared blast-radius rules.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RemediationPlugin(BaseModel, ABC):
    """Abstract base class for all pluggable SRE remediation actions.

    Each action defines its own schema, guardrails, and blast-radius evaluation.
    """

    action_name: str = Field(description="Unique name identifying this action primitive")
    description: str = Field(description="Clear explanation of what the remediation accomplishes")
    risk_level: str = Field(default="LOW", description="Inherent risk level: LOW, MEDIUM, or HIGH")
    allowed_services: List[str] = Field(default_factory=lambda: ["*"], description="Services this action is allowed to target")
    requires_approval: bool = Field(default=False, description="Whether this action always requires human gate approval")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def execute(self, cloud: Any, target: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the remediation action against the cloud provider."""
        ...

    def evaluate_blast_radius(self, cloud: Any, target: str) -> Dict[str, Any]:
        """Evaluate the architectural impact of targeting the given service."""
        topology = cloud.get_topology()
        dependents = [svc for svc, deps in topology.items() if target in deps]

        is_allowed = ("*" in self.allowed_services) or (target in self.allowed_services)
        safe = is_allowed and not self.requires_approval

        rationale = [f"Plugin '{self.action_name}': {self.description}"]
        if not is_allowed:
            safe = False
            rationale.append(f"Target '{target}' is not in allowed services: {self.allowed_services}")
        if dependents:
            rationale.append(f"Direct dependent callers: {', '.join(dependents)}")

        return {
            "target": target,
            "action": self.action_name,
            "risk_level": self.risk_level,
            "safe_to_proceed": safe,
            "direct_dependents": dependents,
            "dependent_count": len(dependents),
            "safety_rationale": rationale,
        }
