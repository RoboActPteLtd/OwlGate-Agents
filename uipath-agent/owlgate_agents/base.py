"""Shared base for OwlGate agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    """Common contract for every OwlGate agent.

    Subclasses implement :meth:`run`. Failures must raise an
    :class:`owlgate_agents.errors.OwlGateError` subclass — never return a
    sentinel.
    """

    #: Human-readable agent name, surfaced in traces and the dashboard.
    name: str = "agent"

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model

    @abstractmethod
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent against ``payload`` and return a result dict."""
        raise NotImplementedError
