"""RiskAgent — maps a diff to impacted test suites and scores release risk."""

from __future__ import annotations

from typing import Any

from owlgate_agents.base import Agent
from owlgate_agents.errors import RiskAssessmentError


class RiskAgent(Agent):
    """Decide *what is worth testing* for a given change.

    Input payload:
        ``diff``: list of changed file paths.
        ``catalogue``: the test catalogue (suite -> source mapping + risk tags).

    Output:
        ``suites``: the impacted suites to run.
        ``score``: a 0..1 release-risk score.
        ``rationale``: why these suites and this score.
    """

    name = "risk"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        diff = payload.get("diff")
        if not diff:
            raise RiskAssessmentError("empty diff: nothing to assess")
        # TODO: LangGraph flow — map changed files to suites via the catalogue,
        # weight by churn / risk tags / historical flakiness, emit a score.
        raise NotImplementedError("RiskAgent.run is a scaffold stub")
