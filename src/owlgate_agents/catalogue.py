"""The test catalogue — the map from source globs to test suites.

This is the knowledge the RiskAgent reasons over: which suites cover which source,
how risky each suite's area is, and how flaky it has been.
"""

from __future__ import annotations

import fnmatch
import json
from collections.abc import Iterable
from pathlib import Path

from owlgate_agents.errors import RiskAssessmentError
from owlgate_agents.models import ChangedFile, SuiteSpec

#: Severity weight per risk tag, in ``0..1``. The catalogue tags each suite; the
#: highest-severity tag among the impacted suites drives the tag component of the
#: risk score. Unknown tags default to ``DEFAULT_TAG_SEVERITY``.
TAG_SEVERITY: dict[str, float] = {
    "auth": 1.0,
    "payment": 1.0,
    "security": 1.0,
    "validation": 0.8,
    "data": 0.7,
    "api": 0.6,
    "form": 0.5,
    "submit": 0.4,
    "ui": 0.3,
    "docs": 0.1,
}

DEFAULT_TAG_SEVERITY = 0.5


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


class TestCatalogue:
    """An immutable collection of :class:`SuiteSpec`, queryable by changed files."""

    def __init__(self, suites: Iterable[SuiteSpec]) -> None:
        self._suites: tuple[SuiteSpec, ...] = tuple(suites)
        if not self._suites:
            raise RiskAssessmentError("test catalogue is empty")
        seen: set[str] = set()
        for s in self._suites:
            if s.id in seen:
                raise RiskAssessmentError(f"duplicate suite id in catalogue: {s.id}")
            seen.add(s.id)

    # -- construction ------------------------------------------------------

    @classmethod
    def from_list(cls, data: Iterable[dict]) -> "TestCatalogue":
        """Build from a list of plain dicts (e.g. parsed JSON).

        A dict missing the required ``id`` (or otherwise malformed) is reported as
        an unusable catalogue, not a bare ``KeyError`` — callers handle the typed
        :class:`RiskAssessmentError`.
        """
        try:
            suites = [
                SuiteSpec(
                    id=d["id"],
                    sources=tuple(d.get("sources", ())),
                    tags=tuple(d.get("tags", ())),
                    flakiness=float(d.get("flakiness", 0.0)),
                )
                for d in data
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise RiskAssessmentError(f"malformed catalogue suite: {exc}") from exc
        return cls(suites)

    @classmethod
    def from_json(cls, source: str | Path) -> "TestCatalogue":
        """Build from a JSON file path or a raw JSON string.

        The JSON is either a list of suites or ``{"suites": [...]}``.
        """
        text = (
            Path(source).read_text(encoding="utf-8")
            if isinstance(source, Path) or _looks_like_path(str(source))
            else str(source)
        )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RiskAssessmentError(f"invalid catalogue JSON: {exc}") from exc
        if isinstance(parsed, dict):
            if "suites" not in parsed:
                raise RiskAssessmentError(
                    "catalogue JSON object must have a 'suites' key"
                )
            data = parsed["suites"]
        else:
            data = parsed
        return cls.from_list(data)

    # -- queries -----------------------------------------------------------

    @property
    def suites(self) -> tuple[SuiteSpec, ...]:
        return self._suites

    def __len__(self) -> int:
        return len(self._suites)

    def severity(self, suite: SuiteSpec) -> float:
        """Highest tag severity for ``suite`` (``0.0`` if it has no tags)."""
        if not suite.tags:
            return 0.0
        return max(TAG_SEVERITY.get(t, DEFAULT_TAG_SEVERITY) for t in suite.tags)

    def covers(self, suite: SuiteSpec, path: str) -> bool:
        """Whether ``suite`` covers ``path`` (any source glob matches)."""
        norm = _normalize(path)
        return any(fnmatch.fnmatch(norm, _normalize(g)) for g in suite.sources)

    def impacted_by(self, files: Iterable[ChangedFile]) -> tuple[SuiteSpec, ...]:
        """Suites covering at least one changed file, in catalogue order."""
        paths = [f.path for f in files]
        return tuple(s for s in self._suites if any(self.covers(s, p) for p in paths))

    def untested(self, files: Iterable[ChangedFile]) -> tuple[str, ...]:
        """Changed files no suite covers — the coverage-gap signal."""
        return tuple(
            f.path
            for f in files
            if not any(self.covers(s, f.path) for s in self._suites)
        )


def _looks_like_path(s: str) -> bool:
    # A heuristic so callers can pass either a path or a raw JSON string.
    stripped = s.lstrip()
    return not (stripped.startswith("{") or stripped.startswith("["))
