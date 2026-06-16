"""Tests for the GateAgent verdict logic."""

from __future__ import annotations

import unittest

from owlgate_agents import GateAgent
from owlgate_agents.errors import GateDecisionError
from owlgate_agents.models import GateVerdict, RiskAssessment


class GateAgentInputTests(unittest.TestCase):
    def test_missing_results_raises(self) -> None:
        with self.assertRaises(GateDecisionError):
            GateAgent().run({})

    def test_bad_risk_type_raises(self) -> None:
        with self.assertRaises(GateDecisionError):
            GateAgent().run({"results": {"passed": 1, "failed": 0}, "risk": 7})


class GateAgentVerdictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = GateAgent()

    def test_all_pass_low_risk_is_go_no_human(self) -> None:
        v = self.agent.run(
            {"results": {"passed": 5, "failed": 0}, "risk": {"high_risk": False, "score": 0.2}}
        )
        self.assertIsInstance(v, GateVerdict)
        self.assertEqual(v.verdict, "go")
        self.assertFalse(v.needs_human)
        self.assertEqual(v.blocking, ())

    def test_unhealed_failure_is_nogo_needs_human(self) -> None:
        v = self.agent.run(
            {
                "results": {"passed": 4, "failed": 2},
                "heals": {"healed": 1},
                "risk": {"high_risk": True, "score": 0.7},
            }
        )
        self.assertEqual(v.verdict, "no-go")
        self.assertTrue(v.needs_human)
        self.assertTrue(any("still failing" in b for b in v.blocking))

    def test_all_failures_healed_is_go(self) -> None:
        v = self.agent.run(
            {
                "results": {"passed": 4, "failed": 2},
                "heals": {"healed": 2},
                "risk": {"high_risk": False, "score": 0.3},
            }
        )
        self.assertEqual(v.verdict, "go")
        self.assertFalse(v.needs_human)

    def test_high_risk_all_pass_is_go_but_needs_human(self) -> None:
        v = self.agent.run(
            {"results": {"passed": 5, "failed": 0}, "risk": {"high_risk": True, "score": 0.62}}
        )
        self.assertEqual(v.verdict, "go")
        self.assertTrue(v.needs_human)

    def test_accepts_risk_assessment_object(self) -> None:
        risk = RiskAssessment(
            suites=("api/contacts",), score=0.7, high_risk=True, untested=(), rationale="x"
        )
        v = self.agent.run({"results": {"passed": 3, "failed": 0}, "risk": risk})
        self.assertTrue(v.needs_human)

    def test_to_dict_shape(self) -> None:
        v = self.agent.run({"results": {"passed": 1, "failed": 0}})
        d = v.to_dict()
        self.assertEqual(set(d), {"verdict", "needs_human", "rationale", "blocking"})


if __name__ == "__main__":
    unittest.main()
