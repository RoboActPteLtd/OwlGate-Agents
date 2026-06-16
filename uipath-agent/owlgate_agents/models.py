"""Immutable value objects shared across OwlGate agents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChangedFile:
    """A single file in a change set.

    ``lines`` is added+removed lines for that file; ``0`` means "unknown" and is
    treated as no churn signal (the orchestrator supplies real counts at runtime).
    """

    path: str
    lines: int = 0

    @classmethod
    def coerce(cls, item: "str | dict | ChangedFile") -> "ChangedFile":
        """Accept a path string, a ``{path, lines}`` dict, or a ChangedFile."""
        if isinstance(item, ChangedFile):
            return item
        if isinstance(item, str):
            return cls(path=item)
        if isinstance(item, dict):
            return cls(path=item["path"], lines=int(item.get("lines", 0)))
        raise TypeError(f"cannot coerce {type(item)!r} to ChangedFile")


@dataclass(frozen=True)
class SuiteSpec:
    """A test suite and the source it covers.

    ``sources`` are glob patterns (forward-slash, repo-relative). ``flakiness`` is
    the historical flaky rate in ``0..1``.
    """

    id: str
    sources: tuple[str, ...]
    tags: tuple[str, ...] = ()
    flakiness: float = 0.0


@dataclass(frozen=True)
class RiskAssessment:
    """The RiskAgent's verdict for a change set."""

    suites: tuple[str, ...]
    score: float
    high_risk: bool
    untested: tuple[str, ...]
    rationale: str

    def to_dict(self) -> dict:
        """Serialize for the orchestrator / dashboard."""
        return {
            "suites": list(self.suites),
            "score": round(self.score, 4),
            "high_risk": self.high_risk,
            "untested": list(self.untested),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class TestFailure:
    """A failed Test Cloud run, as seen by the HealingAgent."""

    suite: str
    message: str
    locator: str | None = None
    source: str = ""

    @classmethod
    def coerce(cls, item: "dict | TestFailure") -> "TestFailure":
        if isinstance(item, TestFailure):
            return item
        if isinstance(item, dict):
            return cls(
                suite=item.get("suite", ""),
                message=item.get("message", ""),
                locator=item.get("locator"),
                source=item.get("source", ""),
            )
        raise TypeError(f"cannot coerce {type(item)!r} to TestFailure")


@dataclass(frozen=True)
class HealProposal:
    """A proposed fix for a non-functional test failure."""

    suite: str
    kind: str  # "selector" | "timing"
    confidence: float
    summary: str
    suggestion: str
    suggested_locator: str | None = None

    def to_dict(self) -> dict:
        return {
            "suite": self.suite,
            "kind": self.kind,
            "confidence": round(self.confidence, 4),
            "summary": self.summary,
            "suggestion": self.suggestion,
            "suggested_locator": self.suggested_locator,
        }


@dataclass(frozen=True)
class RunResult:
    """The outcome of executing a set of suites (a Test Cloud run)."""

    passed: int
    failed: int
    failures: tuple["TestFailure", ...] = ()


@dataclass(frozen=True)
class GateVerdict:
    """The release verdict — the "OwlGate pass"."""

    verdict: str  # "go" | "no-go"
    needs_human: bool
    rationale: str
    blocking: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "needs_human": self.needs_human,
            "rationale": self.rationale,
            "blocking": list(self.blocking),
        }
