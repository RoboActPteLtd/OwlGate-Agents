"""End-to-end tests for the OwlGatePipeline."""

from __future__ import annotations

import unittest
from pathlib import Path

from owlgate_agents import OwlGatePipeline, ScriptedTestRunner, TestCatalogue

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CATALOGUE = REPO_ROOT / "catalogues" / "sample-app.json"


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = TestCatalogue.from_json(SAMPLE_CATALOGUE)

    def _payload(self, diff):
        return {"diff": diff, "catalogue": self.cat}

    def test_all_green_low_risk_is_go(self) -> None:
        runner = ScriptedTestRunner({})  # everything passes
        pipe = OwlGatePipeline(runner)
        report = pipe.run(self._payload([{"path": "src/routes/+page.svelte", "lines": 3}]))
        self.assertEqual(report["verdict"]["verdict"], "go")
        self.assertFalse(report["verdict"]["needs_human"])
        self.assertEqual(report["healed"], [])
        self.assertEqual(report["escalated"], [])

    def test_selector_failure_self_heals(self) -> None:
        runner = ScriptedTestRunner(
            {
                "ui/contact-form": {
                    "suite": "ui/contact-form",
                    "message": "locator '.toast-success > span' resolved to 0 elements",
                    "source": '<div role="status"><span>x</span></div>',
                }
            }
        )
        pipe = OwlGatePipeline(runner)
        report = pipe.run(
            self._payload([{"path": "src/routes/contact/+page.svelte", "lines": 6}])
        )
        self.assertEqual(len(report["healed"]), 1)
        self.assertEqual(report["escalated"], [])
        self.assertEqual(report["verdict"]["verdict"], "go")

    def test_functional_failure_escalates_to_nogo(self) -> None:
        # The demo scenario: tightened validation -> api/contacts fails functionally.
        runner = ScriptedTestRunner(
            {
                "api/contacts": {
                    "suite": "api/contacts",
                    "message": "expected status 201 but received status 400",
                }
            }
        )
        pipe = OwlGatePipeline(runner)
        report = pipe.run(
            self._payload(
                [{"path": "src/routes/api/contacts/+server.ts", "lines": 18}]
            )
        )
        self.assertEqual(len(report["escalated"]), 1)
        self.assertEqual(report["verdict"]["verdict"], "no-go")
        self.assertTrue(report["verdict"]["needs_human"])

    def test_report_shape(self) -> None:
        report = OwlGatePipeline(ScriptedTestRunner({})).run(
            self._payload([{"path": "src/routes/+page.svelte", "lines": 1}])
        )
        self.assertEqual(
            set(report),
            {"risk", "results", "healed", "escalated", "flaky", "verdict"},
        )


if __name__ == "__main__":
    unittest.main()
