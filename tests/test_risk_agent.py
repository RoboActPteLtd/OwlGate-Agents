"""Tests for the RiskAgent selection + scoring engine."""

from __future__ import annotations

import unittest
from pathlib import Path

from owlgate_agents import RiskAgent, TestCatalogue
from owlgate_agents.errors import RiskAssessmentError
from owlgate_agents.models import RiskAssessment

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CATALOGUE = REPO_ROOT / "catalogues" / "sample-app.json"


class RiskAgentInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RiskAgent()
        self.cat = TestCatalogue.from_json(SAMPLE_CATALOGUE)

    def test_empty_diff_raises(self) -> None:
        with self.assertRaises(RiskAssessmentError):
            self.agent.run({"diff": [], "catalogue": self.cat})

    def test_missing_catalogue_raises(self) -> None:
        with self.assertRaises(RiskAssessmentError):
            self.agent.run({"diff": ["a.ts"]})

    def test_malformed_diff_entry_raises(self) -> None:
        with self.assertRaises(RiskAssessmentError):
            self.agent.run({"diff": [123], "catalogue": self.cat})

    def test_accepts_string_dict_and_path_catalogue(self) -> None:
        diff = [{"path": "src/routes/api/contacts/+server.ts", "lines": 10}]
        by_obj = self.agent.run({"diff": diff, "catalogue": self.cat})
        by_path = self.agent.run({"diff": diff, "catalogue": str(SAMPLE_CATALOGUE)})
        by_list = self.agent.run(
            {"diff": diff, "catalogue": [s.__dict__ | {"sources": list(s.sources), "tags": list(s.tags)} for s in self.cat.suites]}
        )
        self.assertEqual(by_obj.suites, by_path.suites)
        self.assertEqual(by_obj.suites, by_list.suites)


class RiskAgentScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RiskAgent()
        self.cat = TestCatalogue.from_json(SAMPLE_CATALOGUE)

    def _run(self, diff) -> RiskAssessment:
        return self.agent.run({"diff": diff, "catalogue": self.cat})

    def test_selects_correct_suite(self) -> None:
        r = self._run([{"path": "src/routes/api/contacts/+server.ts", "lines": 18}])
        self.assertEqual(r.suites, ("api/contacts",))

    def test_score_within_bounds(self) -> None:
        r = self._run([{"path": "src/routes/api/contacts/+server.ts", "lines": 9999}])
        self.assertGreaterEqual(r.score, 0.0)
        self.assertLessEqual(r.score, 1.0)

    def test_high_severity_outranks_low(self) -> None:
        validation = self._run(
            [{"path": "src/routes/api/contacts/+server.ts", "lines": 10}]
        )
        ui_only = self._run([{"path": "src/routes/+page.svelte", "lines": 10}])
        self.assertGreater(validation.score, ui_only.score)

    def test_more_churn_increases_score(self) -> None:
        low = self._run([{"path": "src/routes/api/contacts/+server.ts", "lines": 5}])
        high = self._run([{"path": "src/routes/api/contacts/+server.ts", "lines": 350}])
        self.assertGreater(high.score, low.score)

    def test_coverage_gap_flags_untested(self) -> None:
        r = self._run([{"path": "src/lib/util/secret.ts", "lines": 40}])
        self.assertEqual(r.suites, ())
        self.assertEqual(r.untested, ("src/lib/util/secret.ts",))
        self.assertGreater(r.score, 0.0)  # a gap is itself risk

    def test_high_risk_flag_set_for_validation_change(self) -> None:
        r = self._run([{"path": "src/routes/api/contacts/+server.ts", "lines": 200}])
        self.assertTrue(r.high_risk)

    def test_deterministic(self) -> None:
        diff = [{"path": "src/routes/api/contacts/+server.ts", "lines": 18}]
        self.assertEqual(self._run(diff).score, self._run(diff).score)

    def test_to_dict_shape(self) -> None:
        r = self._run([{"path": "src/routes/api/contacts/+server.ts", "lines": 18}])
        d = r.to_dict()
        self.assertEqual(
            set(d),
            {"suites", "score", "high_risk", "untested", "rationale", "review_targets"},
        )
        self.assertIsInstance(d["suites"], list)


if __name__ == "__main__":
    unittest.main()
