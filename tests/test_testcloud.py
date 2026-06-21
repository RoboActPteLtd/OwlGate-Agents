"""Tests for TestCloudRunner — the suite<->test-case mapping logic.

The HTTP executor is faked, so these verify the run/mapping without a tenant.
"""

from __future__ import annotations

import unittest
from unittest import mock

from owlgate_agents import TestCloudRunner
from owlgate_agents.models import RunResult
from owlgate_agents.testcloud import OrchestratorTestExecutor


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
        # api/contacts failed, but it isn't selected -> not reported. The selected
        # suite's own mapped case passed.
        res = self._runner(
            {"TC_ContactForm": "Passed", "TC_ContactsValidation": "Failed"}
        ).run(["ui/contact-form"])
        self.assertEqual(res.failed, 0)
        self.assertEqual(res.passed, 1)

    def test_mapped_case_with_no_status_fails_closed(self) -> None:
        # ui/contact-form is selected and mapped to TC_ContactForm, but the
        # executor reported no status for it (it did not run). An un-run case must
        # not be treated as a pass by a release gate.
        res = self._runner({}).run(["ui/contact-form"])
        self.assertEqual(res.passed, 0)
        self.assertEqual(res.failed, 1)
        self.assertEqual(res.failures[0].suite, "ui/contact-form")

    def test_mapped_case_with_non_pass_status_fails_closed(self) -> None:
        # A terminal-but-not-passed status (e.g. errored / cancelled) is not a pass.
        res = self._runner({"TC_ContactForm": "Error"}).run(["ui/contact-form"])
        self.assertEqual(res.failed, 1)

    def test_unmapped_suite_counts_as_passed(self) -> None:
        res = self._runner({}).run(["ui/unknown-suite"])
        self.assertEqual(res.failed, 0)
        self.assertEqual(res.passed, 1)

    def test_executor_receives_the_test_set_name(self) -> None:
        ex = FakeExecutor({})
        TestCloudRunner(ex, "OwlGate smoke", SUITE_MAP).run(["api/health"])
        self.assertEqual(ex.ran, "OwlGate smoke")


class RecordingExecutor(OrchestratorTestExecutor):
    """An OrchestratorTestExecutor whose HTTP `_req` is replaced by a scripted
    responder, so the URL/query building and polling logic can be tested with no
    tenant. ``status_sequence`` is the Status returned by successive execution
    polls (defaults to a single terminal "Passed")."""

    def __init__(self, status_sequence=("Passed",), **kw):
        super().__init__(base="https://tenant.example/acct/ten", token="t", **kw)
        self.calls: list[tuple[str, str, dict | None]] = []
        self._statuses = list(status_sequence)

    def _req(self, method, path, query=None, body=None):
        self.calls.append((method, path, query))
        if path == "/odata/TestSets":
            return {"value": [{"Id": 7}]}
        if "StartTestSetExecution" in path:
            return {"value": 99}
        if path.startswith("/odata/TestSetExecutions("):
            status = self._statuses.pop(0) if self._statuses else "Running"
            return {
                "Status": status,
                "TestCaseExecutions": [{"Name": "TC_A", "Status": "Passed"}],
            }
        return {}


class OrchestratorTestExecutorTests(unittest.TestCase):
    def _filter_for(self, executor: RecordingExecutor) -> str:
        get = next(c for c in executor.calls if c[1] == "/odata/TestSets")
        return get[2]["$filter"]

    def test_test_set_name_with_quote_is_escaped(self) -> None:
        # A single quote in the name must be doubled per OData literal rules, so it
        # cannot break out of the quoted filter (injection).
        ex = RecordingExecutor()
        ex.run_test_set("O'Brien smoke")
        self.assertEqual(self._filter_for(ex), "Name eq 'O''Brien smoke'")

    def test_plain_name_is_unquoted_normally(self) -> None:
        ex = RecordingExecutor()
        ex.run_test_set("OwlGate smoke")
        self.assertEqual(self._filter_for(ex), "Name eq 'OwlGate smoke'")

    @mock.patch("owlgate_agents.testcloud.time.sleep", return_value=None)
    def test_non_terminal_status_eventually_raises(self, _sleep) -> None:
        # The execution never reaches a terminal state within max_polls. The
        # executor must NOT return (possibly empty) partial results as if the run
        # finished — that would let an unfinished run pass the gate. Fail closed.
        ex = RecordingExecutor(status_sequence=(), max_polls=3, poll_seconds=0)
        with self.assertRaises(RuntimeError):
            ex.run_test_set("OwlGate smoke")

    @mock.patch("owlgate_agents.testcloud.time.sleep", return_value=None)
    def test_terminal_status_returns_case_statuses(self, _sleep) -> None:
        ex = RecordingExecutor(status_sequence=("Running", "Passed"), poll_seconds=0)
        result = ex.run_test_set("OwlGate smoke")
        self.assertEqual(result, {"TC_A": "Passed"})


if __name__ == "__main__":
    unittest.main()
