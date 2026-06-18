"""RiskAgent — maps a diff to impacted test suites and scores release risk.

The scoring is **deterministic and auditable** by design: a release-gate decision
must be explainable, so the score is a transparent weighted blend of four signals
rather than an opaque model output. An LLM may later enrich the rationale, but the
number a human overrides at the gate is reproducible.
"""

from __future__ import annotations

from typing import Any

from owlgate_agents.base import Agent
from owlgate_agents.catalogue import TestCatalogue
from owlgate_agents.errors import RiskAssessmentError
from owlgate_agents.models import ChangedFile, RiskAssessment

#: Lines of churn that saturate the churn signal to 1.0.
CHURN_SATURATION = 400.0

#: score weights (sum to 1.0) — tag severity dominates: a sizable change in a
#: high-severity area is high-risk on its own; churn, breadth, and coverage gaps
#: nudge the score around that anchor.
W_TAG = 0.50
W_CHURN = 0.20
W_GAP = 0.15
W_BREADTH = 0.15

#: At/above this score the change is flagged high-risk (GateAgent makes the final
#: call; this is an advisory flag).
HIGH_RISK_THRESHOLD = 0.5


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class RiskAgent(Agent):
    """Decide *what is worth testing* for a change, and how risky it is.

    Input payload:
        ``diff``: list of changed files — each a path string or ``{path, lines}``.
        ``catalogue``: a :class:`TestCatalogue`, a list of suite dicts, or a path /
            JSON string accepted by :meth:`TestCatalogue.from_json`.

    Returns a :class:`RiskAssessment` (use ``.to_dict()`` for transport).

    Raises:
        :class:`RiskAssessmentError` when the diff is empty or the catalogue is
        missing / unusable.
    """

    name = "risk"

    def run(self, payload: dict[str, Any]) -> RiskAssessment:
        files = self._parse_diff(payload.get("diff"))
        catalogue = self._parse_catalogue(payload.get("catalogue"))

        impacted = catalogue.impacted_by(files)
        untested = catalogue.untested(files)

        tag_risk = max((catalogue.severity(s) for s in impacted), default=0.0)
        breadth = len(impacted) / len(catalogue)
        churn = _clamp01(sum(f.lines for f in files) / CHURN_SATURATION)
        gap_ratio = len(untested) / len(files)

        score = _clamp01(
            W_TAG * tag_risk
            + W_GAP * gap_ratio
            + W_CHURN * churn
            + W_BREADTH * breadth
        )
        high_risk = score >= HIGH_RISK_THRESHOLD

        return RiskAssessment(
            suites=tuple(s.id for s in impacted),
            score=score,
            high_risk=high_risk,
            untested=untested,
            rationale=self._explain(
                impacted, untested, tag_risk, breadth, churn, gap_ratio, score
            ),
            review_targets=self._review_targets(impacted, files, catalogue),
        )

    @staticmethod
    def _review_targets(impacted, files, catalogue) -> tuple[dict, ...]:
        """The exact code to review: each changed hunk inside an impacted suite,
        as ``{file, function, lines}`` — so the gate can name the function, not just
        the file. Empty when the diff carried no hunk detail."""
        targets: list[dict] = []
        for f in files:
            if not f.hunks:
                continue
            if not any(catalogue.covers(s, f.path) for s in impacted):
                continue
            for h in f.hunks:
                targets.append(
                    {
                        "file": f.path,
                        "function": h.function or "(top level)",
                        "lines": h.line_range,
                    }
                )
        return tuple(targets)

    # -- input parsing -----------------------------------------------------

    @staticmethod
    def _parse_diff(diff: Any) -> list[ChangedFile]:
        if not diff:
            raise RiskAssessmentError("empty diff: nothing to assess")
        try:
            return [ChangedFile.coerce(item) for item in diff]
        except (TypeError, KeyError) as exc:
            raise RiskAssessmentError(f"malformed diff entry: {exc}") from exc

    @staticmethod
    def _parse_catalogue(catalogue: Any) -> TestCatalogue:
        if catalogue is None:
            raise RiskAssessmentError("no test catalogue provided")
        if isinstance(catalogue, TestCatalogue):
            return catalogue
        if isinstance(catalogue, str):
            return TestCatalogue.from_json(catalogue)
        if isinstance(catalogue, (list, tuple)):
            return TestCatalogue.from_list(list(catalogue))
        raise RiskAssessmentError(
            f"unsupported catalogue type: {type(catalogue)!r}"
        )

    # -- explanation -------------------------------------------------------

    @staticmethod
    def _explain(
        impacted,
        untested,
        tag_risk: float,
        breadth: float,
        churn: float,
        gap_ratio: float,
        score: float,
    ) -> str:
        if impacted:
            sel = f"{len(impacted)} suite(s) impacted: " + ", ".join(
                s.id for s in impacted
            )
        else:
            sel = "no suites impacted by this change"
        parts = [
            sel,
            f"tag risk {tag_risk:.2f}",
            f"breadth {breadth:.2f}",
            f"churn {churn:.2f}",
            f"coverage-gap {gap_ratio:.2f}",
        ]
        if untested:
            parts.append(f"{len(untested)} changed file(s) covered by no suite")
        return f"risk {score:.2f} — " + "; ".join(parts)
