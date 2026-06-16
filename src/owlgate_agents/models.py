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
