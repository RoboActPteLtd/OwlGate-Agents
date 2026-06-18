"""OwlGate coded agents — the reasoning brain of the release-gate.

Exposes the three agents, the shared base, the test catalogue, and value objects.
All failure modes surface as typed exceptions from :mod:`owlgate_agents.errors`.
"""

from owlgate_agents.base import Agent
from owlgate_agents.catalogue import TestCatalogue
from owlgate_agents.flaky import FlakyDetector
from owlgate_agents.gate_agent import GateAgent
from owlgate_agents.healing_agent import HealingAgent
from owlgate_agents.models import (
    ChangedFile,
    GateVerdict,
    HealProposal,
    Hunk,
    RiskAssessment,
    RunResult,
    SuiteSpec,
    TestFailure,
)
from owlgate_agents.pipeline import OwlGatePipeline, ScriptedTestRunner, TestRunner
from owlgate_agents.risk_agent import RiskAgent
from owlgate_agents.testcloud import (
    OrchestratorTestExecutor,
    TestCloudRunner,
    TestExecutor,
)

__all__ = [
    "Agent",
    "RiskAgent",
    "HealingAgent",
    "GateAgent",
    "FlakyDetector",
    "OwlGatePipeline",
    "ScriptedTestRunner",
    "TestRunner",
    "TestCloudRunner",
    "TestExecutor",
    "OrchestratorTestExecutor",
    "TestCatalogue",
    "SuiteSpec",
    "ChangedFile",
    "RiskAssessment",
    "TestFailure",
    "HealProposal",
    "GateVerdict",
    "RunResult",
    "Hunk",
]
__version__ = "0.0.1"
