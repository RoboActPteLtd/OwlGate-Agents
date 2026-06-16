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
- Minimal GitHub Actions CI — byte-compile and run the `unittest` suite.

### Changed

- Relicensed from MIT to Apache 2.0.
