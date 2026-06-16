"""HealingAgent — diagnoses a broken test and proposes a fix."""

from __future__ import annotations

from typing import Any

from owlgate_agents.base import Agent
from owlgate_agents.errors import HealingError, UnhealableTestError


class HealingAgent(Agent):
    """Repair tests that break for non-functional reasons (e.g. a moved selector).

    Input payload:
        ``failure``: the Test Cloud failure (locator, message, screenshot ref).
        ``source``: the test definition + relevant app source.

    Output:
        ``patch``: the proposed fix (authored via a coding agent).
        ``confidence``: 0..1.

    Raises:
        :class:`UnhealableTestError` when the failure looks functional (a real
        bug) — the orchestrator then escalates to the human gate instead of
        masking a regression.
    """

    name = "heal"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        failure = payload.get("failure")
        if not failure:
            raise HealingError("no failure context provided")
        # TODO: classify functional vs. test-defect; if functional, raise
        # UnhealableTestError. Otherwise delegate patch authoring to the coding
        # agent and return the diff for re-run.
        raise NotImplementedError("HealingAgent.run is a scaffold stub")
