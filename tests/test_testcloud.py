"""Tests for TestCloudRunner — the suite<->test-case mapping logic.

The HTTP executor is faked, so these verify the run/mapping without a tenant.
"""

from __future__ import annotations

import unittest

from owlgate_agents import TestCloudRunner
from owlgate_agents.models import RunResult


class FakeExecutor:
    """A TestExecutor that returns canned per-case statuses."""

    def __init__(self, statuses: dict[str, str]) -> None:
        self._statuses = statuses
        self.ran: str | None = None

    def run_test_set(self, test_set: str):
        self.ran = test_set
        return self._statuses


SUITE_MAP = {
    "ui/contact-form": ["TC_ContactForm"],
    "api/contacts": ["TC_ContactsValidation"],
    "api/health": ["TC_Health"],
}


class TestCloudRunnerTests(unittest.TestCase):
    def _runner(self, statuses):
        return TestCloudRunner(FakeExecutor(statuses), "OwlGate smoke", SUITE_MAP)

    def test_all_pass(self) -> None:
        r = self._runner({"TC_ContactForm": "Passed", "TC_ContactsValidation": "Passed"})
        res = r.run(["ui/contact-form", "api/contacts"])
        self.assertIsInstance(res, RunResult)
        self.assertEqual(res.failed, 0)
        self.assertEqual(res.passed, 2)
        self.assertEqual(res.failures, ())

    def test_a_failed_case_fails_its_suite(self) -> None:
        res = self._runner(
            {"TC_ContactForm": "Passed", "TC_ContactsValidation": "Failed"}
        ).run(["ui/contact-form", "api/contacts"])
        self.assertEqual(res.failed, 1)
        self.assertEqual(res.failures[0].suite, "api/contacts")
        self.assertIn("TC_ContactsValidation", res.failures[0].message)

    def test_status_case_insensitive(self) -> None:
        res = self._runner({"TC_Health": "failed"}).run(["api/health"])
        self.assertEqual(res.failed, 1)

    def test_only_selected_suites_are_considered(self) -> None:
        # api/contacts failed, but it isn't selected -> not reported.
        res = self._runner({"TC_ContactsValidation": "Failed"}).run(["ui/contact-form"])
        self.assertEqual(res.failed, 0)
        self.assertEqual(res.passed, 1)

    def test_unmapped_suite_counts_as_passed(self) -> None:
        res = self._runner({}).run(["ui/unknown-suite"])
        self.assertEqual(res.failed, 0)
        self.assertEqual(res.passed, 1)

    def test_executor_receives_the_test_set_name(self) -> None:
        ex = FakeExecutor({})
        TestCloudRunner(ex, "OwlGate smoke", SUITE_MAP).run(["api/health"])
        self.assertEqual(ex.ran, "OwlGate smoke")


if __name__ == "__main__":
    unittest.main()
