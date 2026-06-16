"""CLI: run the full OwlGate pipeline on a change description.

    python -m owlgate_agents [input.json]

The input JSON has ``diff`` and ``catalogue`` (as for the RiskAgent) plus an
optional ``outcomes`` map (suite -> "pass" | {message, locator, source}) used to
drive the bundled :class:`ScriptedTestRunner` for local / demo runs. With a real
Test Cloud runner this CLI is replaced by ``uip codedagent run``.
"""

from __future__ import annotations

import json
import sys

from owlgate_agents.errors import OwlGateError
from owlgate_agents.pipeline import OwlGatePipeline, ScriptedTestRunner


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else "examples/diff.json"
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read input {path!r}: {exc}", file=sys.stderr)
        return 2

    outcomes = payload.pop("outcomes", {})
    pipeline = OwlGatePipeline(ScriptedTestRunner(outcomes))
    try:
        report = pipeline.run(payload)
    except OwlGateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
