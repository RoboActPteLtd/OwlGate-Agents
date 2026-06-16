"""Typed exception hierarchy for OwlGate agents.

Exception-driven: callers handle these, never sentinel return values.
"""


class OwlGateError(Exception):
    """Base class for every OwlGate agent failure."""


class RiskAssessmentError(OwlGateError):
    """The Risk agent could not map the diff to suites or score it."""


class HealingError(OwlGateError):
    """The Self-Healing agent could not produce a usable fix."""


class UnhealableTestError(HealingError):
    """The failure is functional (a real bug), not a healable test defect.

    Signals the orchestrator to stop healing and escalate to the human gate.
    """


class GateDecisionError(OwlGateError):
    """The Gate agent could not reach a verdict from the available signals."""
