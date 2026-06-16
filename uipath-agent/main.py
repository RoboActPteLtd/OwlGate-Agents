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
import uuid
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
    # Raise the human-approval record (queue item + Action Center task) on needs_human.
    escalate: bool = False


@dataclass
class GateOut:
    verdict: str
    needs_human: bool
    escalation: str
    report: dict


def _resolve_catalogue(catalogue: list[dict] | None) -> list[dict]:
    if catalogue:
        return catalogue
    return json.loads(_DEFAULT_CATALOGUE.read_text(encoding="utf-8"))["suites"]


def _raise_human_gate(verdict: dict) -> str:
    """Record a human-approval request for a verdict needing sign-off.

    Two surfaces, both best-effort, gated behind OWLGATE_ESCALATE (so local runs /
    evals never touch the tenant; the deployed process sets OWLGATE_ESCALATE=1):

    1. A **queue item** in `owlgate-changes` — a durable, human-reviewable approval
       record that works on any tenant (no Actions service required).
    2. An **Action Center task** — the richer HITL surface, used when the tenant's
       Actions service is enabled.

    The SDK client is built inside the function (never at import) and every call is
    wrapped so the gate still returns its verdict even without UiPath auth/services.
    """
    payload = {
        "verdict": verdict["verdict"],
        "rationale": verdict["rationale"],
        "blocking": "; ".join(verdict.get("blocking", [])) or "none",
    }
    statuses: list[str] = []
    try:
        from uipath.platform import UiPath

        sdk = UiPath()
        try:
            sdk.queues.create_item(
                item={
                    "name": "owlgate-changes",
                    "priority": "Normal",
                    "specific_content": payload,
                    # The queue enforces unique references.
                    "reference": f"owlgate-{uuid.uuid4().hex[:12]}",
                },
                queue_name="owlgate-changes",
                folder_path="Shared",
            )
            statuses.append("queued")
        except Exception as e:  # noqa: BLE001
            statuses.append(f"queue-failed: {type(e).__name__}: {str(e)[:600]}")
        try:
            sdk.tasks.create(
                title="OwlGate release approval", data=payload, source_name="OwlGate"
            )
            statuses.append("action-center")
        except Exception as e:  # noqa: BLE001 — Action Center needs the Actions service
            statuses.append(f"action-center-failed: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001 — escalation is never fatal to the verdict
        statuses.append(f"sdk-init-failed: {type(e).__name__}: {str(e)[:140]}")
    return "; ".join(statuses)


def main(input: GateIn) -> GateOut:
    runner = ScriptedTestRunner(input.outcomes or {})
    report = OwlGatePipeline(runner).run(
        {"diff": input.diff, "catalogue": _resolve_catalogue(input.catalogue)}
    )
    verdict = report["verdict"]
    if not verdict["needs_human"]:
        escalation = "n/a"
    elif input.escalate or os.getenv("OWLGATE_ESCALATE"):
        escalation = _raise_human_gate(verdict)
    else:
        escalation = "skipped: escalation disabled"
    return GateOut(
        verdict=verdict["verdict"],
        needs_human=verdict["needs_human"],
        escalation=escalation,
        report=report,
    )
