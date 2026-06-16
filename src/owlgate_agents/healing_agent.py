"""HealingAgent — diagnoses a broken test and proposes a fix.

Safety property: OwlGate must **never** "heal" a genuine regression into a pass. So
the classifier only heals failures with a clear non-functional signal (a moved
selector, a timing race); anything that looks functional — or is ambiguous — is
escalated via :class:`UnhealableTestError` to the human gate.

The classification is deterministic and signal-based so it is auditable. In the
full system the patch authoring is delegated to a coding agent; here the proposal
is derived from the failure and any source hint.
"""

from __future__ import annotations

import re
from typing import Any

from owlgate_agents.base import Agent
from owlgate_agents.errors import HealingError, UnhealableTestError
from owlgate_agents.models import HealProposal, TestFailure

#: A selector/locator problem — the element moved or was renamed. Healable.
SELECTOR_SIGNALS = (
    "locator",
    "selector",
    "resolved to 0",
    "no element",
    "not found",
    "no node found",
    "unable to find",
)

#: A timing race — the assertion ran before the UI settled. Healable.
TIMING_SIGNALS = (
    "timeout",
    "timed out",
    "waiting for",
    "exceeded",
)

#: A behaviour/value/status difference — likely a real bug. Escalate.
FUNCTIONAL_SIGNALS = (
    "status code",
    "status 4",
    "status 5",
    "http 4",
    "http 5",
    "received",
    "to equal",
    "to be ",
    "validation",
    "rejected",
)

#: confidence per healable kind.
CONFIDENCE = {"selector": 0.8, "timing": 0.6}


class HealingAgent(Agent):
    """Repair tests that break for non-functional reasons.

    Input payload:
        ``failure``: a :class:`TestFailure` or ``{suite, message, locator, source}``.

    Returns a :class:`HealProposal`.

    Raises:
        :class:`HealingError` when no failure context is provided.
        :class:`UnhealableTestError` when the failure looks functional or is
        ambiguous — the orchestrator escalates to the human gate.
    """

    name = "heal"

    def run(self, payload: dict[str, Any]) -> HealProposal:
        failure = self._parse_failure(payload.get("failure"))
        text = failure.message.lower()

        has_selector = any(s in text for s in SELECTOR_SIGNALS)
        has_timing = any(s in text for s in TIMING_SIGNALS)
        has_functional = any(s in text for s in FUNCTIONAL_SIGNALS)

        # A clear functional difference with no test-mechanics signal => real bug.
        if has_functional and not (has_selector or has_timing):
            raise UnhealableTestError(
                f"{failure.suite or 'test'}: failure looks functional "
                f"(a real behaviour change), not a test defect — escalating"
            )

        if has_selector:
            return self._heal_selector(failure)
        if has_timing:
            return self._heal_timing(failure)

        # No actionable signal: do not guess. Escalate.
        raise UnhealableTestError(
            f"{failure.suite or 'test'}: no actionable non-functional signal in "
            f"the failure — escalating rather than masking a possible regression"
        )

    # -- input -------------------------------------------------------------

    @staticmethod
    def _parse_failure(failure: Any) -> TestFailure:
        if not failure:
            raise HealingError("no failure context provided")
        try:
            return TestFailure.coerce(failure)
        except TypeError as exc:
            raise HealingError(str(exc)) from exc

    # -- proposals ---------------------------------------------------------

    @staticmethod
    def _heal_selector(failure: TestFailure) -> HealProposal:
        suggested = _suggest_stable_locator(failure.source)
        suggestion = (
            f"Replace the brittle locator "
            f"{('`' + failure.locator + '`') if failure.locator else ''} with a "
            f"stable one"
        )
        if suggested:
            suggestion += f": `{suggested}`."
        else:
            suggestion += " (prefer a role or data-testid over CSS structure)."
        return HealProposal(
            suite=failure.suite,
            kind="selector",
            confidence=CONFIDENCE["selector"],
            summary="Fragile selector broke when the markup changed.",
            suggestion=suggestion,
            suggested_locator=suggested,
        )

    @staticmethod
    def _heal_timing(failure: TestFailure) -> HealProposal:
        return HealProposal(
            suite=failure.suite,
            kind="timing",
            confidence=CONFIDENCE["timing"],
            summary="Timing race: the assertion ran before the UI settled.",
            suggestion=(
                "Replace fixed sleeps with auto-waiting assertions (e.g. "
                "`await expect(locator).toBeVisible()`), or raise the assertion "
                "timeout for the animated element."
            ),
        )


# A stable locator is, in order of preference: an ARIA role, then a data-testid.
_ROLE_RE = re.compile(r'role=["\']([a-zA-Z]+)["\']')
_TESTID_RE = re.compile(r'data-testid=["\']([^"\']+)["\']')


def _suggest_stable_locator(source: str) -> str | None:
    if not source:
        return None
    testid = _TESTID_RE.search(source)
    if testid:
        return f'getByTestId("{testid.group(1)}")'
    role = _ROLE_RE.search(source)
    if role:
        return f'getByRole("{role.group(1)}")'
    return None
