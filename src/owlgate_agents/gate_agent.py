"""GateAgent — synthesizes all signals into a go / no-go verdict.

Deterministic and explainable: the verdict is a function of three inputs — how many
tests still fail after healing, the residual risk, and (advisory) coverage gaps.
A human always makes the final call at the Action Center gate; this agent produces
the recommendation and the reasons behind it.
"""

from __future__ import annotations

from typing import Any

from owlgate_agents.base import Agent
from owlgate_agents.errors import GateDecisionError
from owlgate_agents.models import GateVerdict, RiskAssessment


class GateAgent(Agent):
    """Issue the release verdict.

    Input payload:
        ``results``: test outcomes — ``{passed, failed}`` (counts).
        ``heals``: healing outcomes — ``{healed}`` (failures fixed and re-run green).
        ``risk``: a :class:`RiskAssessment` or ``{score, high_risk}`` (optional).

    Returns a :class:`GateVerdict`.

    Raises:
        :class:`GateDecisionError` when test results are missing.
    """

    name = "gate"

    def run(self, payload: dict[str, Any]) -> GateVerdict:
        results = payload.get("results")
        if not isinstance(results, dict):
            raise GateDecisionError("cannot decide without test results")

        failed = int(results.get("failed", 0))
        healed = int((payload.get("heals") or {}).get("healed", 0))
        unhealed = max(0, failed - healed)

        high_risk, score = self._parse_risk(payload.get("risk"))

        blocking: list[str] = []
        if unhealed > 0:
            blocking.append(f"{unhealed} test(s) still failing after healing")
        if high_risk:
            blocking.append(f"change risk above threshold (score {score:.2f})")

        # A still-failing test blocks outright. High risk alone does not block, but
        # it cannot be auto-approved — it requires a human sign-off.
        if unhealed > 0:
            verdict, needs_human = "no-go", True
        elif high_risk:
            verdict, needs_human = "go", True
        else:
            verdict, needs_human = "go", False

        return GateVerdict(
            verdict=verdict,
            needs_human=needs_human,
            rationale=self._explain(verdict, needs_human, failed, healed, blocking),
            blocking=tuple(blocking),
        )

    @staticmethod
    def _parse_risk(risk: Any) -> tuple[bool, float]:
        if risk is None:
            return False, 0.0
        if isinstance(risk, RiskAssessment):
            return risk.high_risk, risk.score
        if isinstance(risk, dict):
            return bool(risk.get("high_risk", False)), float(risk.get("score", 0.0))
        raise GateDecisionError(f"unsupported risk type: {type(risk)!r}")

    @staticmethod
    def _explain(
        verdict: str,
        needs_human: bool,
        failed: int,
        healed: int,
        blocking: list[str],
    ) -> str:
        head = "NO-GO" if verdict == "no-go" else "GO"
        if needs_human:
            head += " (human approval required)"
        detail = f"{failed} failure(s), {healed} self-healed"
        if blocking:
            return f"{head} — {detail}; blocking: " + "; ".join(blocking)
        return f"{head} — {detail}; all checks clear"
