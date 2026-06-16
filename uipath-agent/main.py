"""OwlGate release-gate as a UiPath coded agent.

A Coded Function (deterministic, no LLM) that wraps `OwlGatePipeline`: given a
change diff (and optional scripted test outcomes), it selects impacted suites,
heals fragile failures, escalates real ones, and returns the go / no-go verdict.

`owlgate_agents` is vendored alongside this file so the package deploys
self-contained; refresh it from ../src/owlgate_agents (see README).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from owlgate_agents import OwlGatePipeline, ScriptedTestRunner

_DEFAULT_CATALOGUE = Path(__file__).parent / "catalogues" / "sample-app.json"


@dataclass
class GateIn:
    # Changed files: each a {"path": str, "lines": int}.
    diff: list[dict]
    # Test catalogue as a list of suite dicts; defaults to the bundled sample app.
    catalogue: list[dict] | None = None
    # Optional scripted Test Cloud outcomes: suite -> "pass" | {message, locator, source}.
    outcomes: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateOut:
    verdict: str
    needs_human: bool
    report: dict


def _resolve_catalogue(catalogue: list[dict] | None) -> list[dict]:
    if catalogue:
        return catalogue
    return json.loads(_DEFAULT_CATALOGUE.read_text(encoding="utf-8"))["suites"]


def _raise_human_gate(verdict: dict) -> None:
    """Raise an Action Center approval task for a verdict needing human sign-off.

    Gated behind OWLGATE_ESCALATE so local runs / evals never create tenant tasks;
    the deployed process sets OWLGATE_ESCALATE=1. SDK client is built inside the
    function (never at import time) and failures are swallowed so the gate still
    returns its verdict even without UiPath auth.
    """
    if not os.getenv("OWLGATE_ESCALATE"):
        return
    try:
        from uipath.platform import UiPath

        UiPath().tasks.create(
            title="OwlGate release approval",
            data={
                "verdict": verdict["verdict"],
                "rationale": verdict["rationale"],
                "blocking": verdict["blocking"],
            },
            source_name="OwlGate",
        )
    except Exception:  # noqa: BLE001 — escalation is best-effort, never fatal
        pass


def main(input: GateIn) -> GateOut:
    runner = ScriptedTestRunner(input.outcomes or {})
    report = OwlGatePipeline(runner).run(
        {"diff": input.diff, "catalogue": _resolve_catalogue(input.catalogue)}
    )
    verdict = report["verdict"]
    if verdict["needs_human"]:
        _raise_human_gate(verdict)
    return GateOut(
        verdict=verdict["verdict"],
        needs_human=verdict["needs_human"],
        report=report,
    )
