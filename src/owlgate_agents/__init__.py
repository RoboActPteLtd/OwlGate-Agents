"""OwlGate coded agents — the reasoning brain of the release-gate.

Exposes the three agents, the shared base, the test catalogue, and value objects.
All failure modes surface as typed exceptions from :mod:`owlgate_agents.errors`.
"""

from owlgate_agents.base import Agent
from owlgate_agents.catalogue import TestCatalogue
from owlgate_agents.gate_agent import GateAgent
from owlgate_agents.healing_agent import HealingAgent
from owlgate_agents.models import (
    ChangedFile,
    HealProposal,
    RiskAssessment,
    SuiteSpec,
    TestFailure,
)
from owlgate_agents.risk_agent import RiskAgent

__all__ = [
    "Agent",
    "RiskAgent",
    "HealingAgent",
    "GateAgent",
    "TestCatalogue",
    "SuiteSpec",
    "ChangedFile",
    "RiskAssessment",
    "TestFailure",
    "HealProposal",
]
__version__ = "0.0.1"
