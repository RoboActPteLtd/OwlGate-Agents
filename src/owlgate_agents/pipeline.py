"""OwlGatePipeline — the end-to-end release-gate flow.

Wires the three agents into the sequence the orchestrator runs for each change:

    select (Risk) -> execute (Test Cloud) -> heal (Self-Healing) -> decide (Gate)

The test runner is injected so the real Test Cloud client plugs in later; a
:class:`ScriptedTestRunner` drives local runs, demos, and tests deterministically.
"""

from __future__ import annotations

from typing import Any, Protocol

from owlgate_agents.errors import UnhealableTestError
from owlgate_agents.gate_agent import GateAgent
from owlgate_agents.healing_agent import HealingAgent
from owlgate_agents.models import RunResult, TestFailure
from owlgate_agents.risk_agent import RiskAgent


class TestRunner(Protocol):
    """Executes the selected suites and reports pass/fail with failure detail."""

    def run(self, suites: list[str]) -> RunResult: ...


class ScriptedTestRunner:
    """A deterministic runner: maps each suite to ``"pass"`` or a TestFailure."""

    def __init__(self, outcomes: dict[str, "str | TestFailure | dict"]) -> None:
        self._outcomes = outcomes

    def run(self, suites: list[str]) -> RunResult:
        passed = 0
        failures: list[TestFailure] = []
        for suite in suites:
            outcome = self._outcomes.get(suite, "pass")
            if outcome == "pass":
                passed += 1
            else:
                failures.append(TestFailure.coerce(outcome))
        return RunResult(passed=passed, failed=len(failures), failures=tuple(failures))


class OwlGatePipeline:
    """Run a change through the full gate and return a combined report."""

    def __init__(
        self,
        runner: TestRunner,
        *,
        risk: RiskAgent | None = None,
        healing: HealingAgent | None = None,
        gate: GateAgent | None = None,
    ) -> None:
        self._runner = runner
        self._risk = risk or RiskAgent()
        self._healing = healing or HealingAgent()
        self._gate = gate or GateAgent()

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        risk = self._risk.run(payload)

        run_result = self._runner.run(list(risk.suites))

        healed: list[dict] = []
        escalated: list[dict] = []
        for failure in run_result.failures:
            try:
                proposal = self._healing.run({"failure": failure})
                healed.append(proposal.to_dict())
            except UnhealableTestError as exc:
                escalated.append({"suite": failure.suite, "reason": str(exc)})

        verdict = self._gate.run(
            {
                "results": {"passed": run_result.passed, "failed": run_result.failed},
                "heals": {"healed": len(healed)},
                "risk": risk,
            }
        )

        return {
            "risk": risk.to_dict(),
            "results": {"passed": run_result.passed, "failed": run_result.failed},
            "healed": healed,
            "escalated": escalated,
            "verdict": verdict.to_dict(),
        }
