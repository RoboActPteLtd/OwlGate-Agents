"""Tests for the FlakyDetector."""

from __future__ import annotations

import unittest
from pathlib import Path

from owlgate_agents import FlakyDetector, TestCatalogue

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CATALOGUE = REPO_ROOT / "catalogues" / "sample-app.json"


class FlakyDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = TestCatalogue.from_json(SAMPLE_CATALOGUE)

    def test_flags_suite_above_threshold(self) -> None:
        # ui/contact-form has flakiness 0.25 (>= 0.2 default).
        findings = FlakyDetector().detect(self.cat)
        ids = {f["suite"] for f in findings}
        self.assertIn("ui/contact-form", ids)
        self.assertNotIn("api/health", ids)  # flakiness 0.0

    def test_recommendation_quarantine_vs_stabilize(self) -> None:
        finding = next(
            f for f in FlakyDetector().detect(self.cat) if f["suite"] == "ui/contact-form"
        )
        self.assertEqual(finding["recommendation"], "stabilize")  # 0.25 < 0.5

    def test_high_flakiness_quarantines(self) -> None:
        from owlgate_agents.models import SuiteSpec

        cat = TestCatalogue([SuiteSpec("ui/x", ("a/**",), ("ui",), flakiness=0.8)])
        finding = FlakyDetector().detect(cat)[0]
        self.assertEqual(finding["recommendation"], "quarantine")

    def test_limit_to_selected_suites(self) -> None:
        findings = FlakyDetector().detect(self.cat, suites=["api/contacts"])
        # api/contacts flakiness is 0.05 -> not flaky -> empty
        self.assertEqual(findings, [])

    def test_threshold_is_configurable(self) -> None:
        # Lower threshold catches api/contacts (0.05).
        findings = FlakyDetector(threshold=0.0).detect(self.cat, suites=["api/contacts"])
        self.assertEqual(len(findings), 1)


if __name__ == "__main__":
    unittest.main()
