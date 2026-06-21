# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial scaffold of the OwlGate coded agents.
- `Agent` base class and typed exception hierarchy (`errors.py`).
- Stubs for `RiskAgent`, `HealingAgent`, and `GateAgent`.
- **RiskAgent implemented** — deterministic test-impact selection + auditable risk
  scoring. Adds `TestCatalogue` (source-glob → suite mapping with risk tags and
  flakiness), value objects in `models.py` (`ChangedFile`, `SuiteSpec`,
  `RiskAssessment`), a sample-app catalogue (`catalogues/sample-app.json`), an
  example input (`examples/diff.json`), and a 22-case `unittest` suite. The score
  is a transparent weighted blend (tag severity, churn, coverage gap, breadth) so
  it can be audited and overridden at the gate.
- **HealingAgent implemented** — deterministic, signal-based failure classifier:
  heals fragile-selector and timing failures (proposing a stable locator / auto-wait)
  and **escalates functional or ambiguous failures via `UnhealableTestError`** so a
  real regression is never masked. Adds `TestFailure` / `HealProposal` value objects
  and an 8-case test suite.
- **GateAgent implemented** — deterministic go / no-go verdict from test results,
  heal outcomes, and residual risk; unhealed failures block, high risk requires a
  human sign-off. Adds the `GateVerdict` value object.
- **OwlGatePipeline** — end-to-end orchestration (select → execute → heal → decide)
  with an injectable `TestRunner` (`ScriptedTestRunner` for local/demo runs) and a
  `python -m owlgate_agents` CLI that runs the full gate on a change description.
- **FlakyDetector** — flags fragile suites from recorded flakiness (stabilize vs.
  quarantine), surfaced as a `flaky` section in the pipeline report.
- **Line/function-level review targets** — `ChangedFile` now carries optional `Hunk`s
  (function + line range from diff hunk headers), and `RiskAgent` emits
  `review_targets` (`[{file, function, lines}]`) for the changed code inside impacted
  suites. The verdict can now name the **exact function + lines** to review, not just
  the file. Backward-compatible (empty when no hunks are sent).
- **TestCloudRunner** — the real `TestRunner` that executes a UiPath Test Cloud test
  set (Orchestrator Test Automation API, stdlib `urllib`) and maps per-test-case
  results to suites. The HTTP sits behind a `TestExecutor` seam so the run/mapping
  logic is unit-tested (6 cases) without a tenant. Not wired into the deployed agent
  yet — activation needs automated test cases in Test Cloud + a redeploy (replaces
  `ScriptedTestRunner` in `main.py`).
- **Deployable UiPath coded agent** (`uipath-agent/`) — a Coded Function wrapping
  `OwlGatePipeline` (dataclass IO), packaged and **published to UiPath** via
  `uip codedagent deploy`; vendors the package for self-contained deploy and ships
  a smoke eval set (JSON-similarity evaluator). Verified by a successful
  Orchestrator job run on the tenant (verdict `no-go`, `needs_human`).
- **Human-gate escalation** — on `verdict.needs_human` (and `escalate` input true),
  the agent records a human-approval request via the UiPath SDK: a **queue item** in
  `owlgate-changes` (a human-reviewable record that needs no Actions service —
  **verified live by a tenant job**) plus an **Action Center task** (`sdk.tasks.create`,
  used when the tenant's Actions service is enabled). Gated by the `escalate` input
  (env `OWLGATE_ESCALATE` also honoured); the outcome is surfaced in the output's
  `escalation` field.
- Minimal GitHub Actions CI — byte-compile and run the `unittest` suite; gitleaks secret scan.

### Security

- `OrchestratorTestExecutor` now escapes the test-set name as a proper OData string
  literal (single quotes doubled) before interpolating it into the `$filter`, so a
  name containing `'` can no longer break out of the quoted filter (OData injection).

### Fixed

- `TestCatalogue.from_list` / `from_json` now raise the typed `RiskAssessmentError`
  for a malformed catalogue (a suite dict missing `id`, or a JSON object without a
  `suites` key) instead of leaking a bare `KeyError`, so callers can handle the one
  documented failure type.

### Changed

- Relicensed from MIT to Apache 2.0.
