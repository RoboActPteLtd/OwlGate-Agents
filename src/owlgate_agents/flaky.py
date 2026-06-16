"""FlakyDetector — flags fragile suites before they block a release.

Uses the historical flakiness recorded per suite in the catalogue. Suites at or
above the threshold are surfaced with a recommendation: stabilize, or (when very
flaky) quarantine so they stop gating releases until fixed.
"""

from __future__ import annotations

from collections.abc import Iterable

from owlgate_agents.catalogue import TestCatalogue

DEFAULT_FLAKY_THRESHOLD = 0.2
QUARANTINE_THRESHOLD = 0.5


class FlakyDetector:
    """Identify fragile/flaky suites from recorded flakiness."""

    def __init__(self, threshold: float = DEFAULT_FLAKY_THRESHOLD) -> None:
        self._threshold = threshold

    def detect(
        self,
        catalogue: TestCatalogue,
        suites: Iterable[str] | None = None,
    ) -> list[dict]:
        """Return flaky findings, optionally limited to ``suites`` (e.g. selected).

        Each finding: ``{suite, flakiness, recommendation}``.
        """
        limit = set(suites) if suites is not None else None
        findings: list[dict] = []
        for spec in catalogue.suites:
            if limit is not None and spec.id not in limit:
                continue
            if spec.flakiness >= self._threshold:
                findings.append(
                    {
                        "suite": spec.id,
                        "flakiness": round(spec.flakiness, 4),
                        "recommendation": (
                            "quarantine"
                            if spec.flakiness >= QUARANTINE_THRESHOLD
                            else "stabilize"
                        ),
                    }
                )
        return findings
