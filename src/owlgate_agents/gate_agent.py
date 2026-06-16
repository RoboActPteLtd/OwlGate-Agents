"""GateAgent — synthesizes all signals into a go / no-go verdict."""

from __future__ import annotations

from typing import Any

from owlgate_agents.base import Agent
from owlgate_agents.errors import GateDecisionError


class GateAgent(Agent):
    """Issue the release verdict — the "OwlGate pass".

    Input payload:
        ``results``: Test Cloud run results for the selected suites.
        ``heals``: what the HealingAgent fixed (and what it could not).
        ``risk``: the RiskAgent score + rationale.

    Output:
        ``verdict``: ``"go"`` | ``"no-go"``.
        ``rationale``: human-readable justification shown at the gate.
        ``needs_human``: whether approval is mandatory before release.
    """

    name = "gate"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "results" not in payload:
            raise GateDecisionError("cannot decide without test results")
        # TODO: weigh residual risk, unhealed failures, and coverage gaps into a
        # verdict; always set needs_human=True above a risk threshold.
        raise NotImplementedError("GateAgent.run is a scaffold stub")
