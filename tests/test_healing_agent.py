"""Tests for the HealingAgent classifier and the escalation safety property."""

from __future__ import annotations

import unittest

from owlgate_agents import HealingAgent
from owlgate_agents.errors import HealingError, UnhealableTestError
from owlgate_agents.models import HealProposal


class HealingAgentInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = HealingAgent()

    def test_missing_failure_raises_healing_error(self) -> None:
        with self.assertRaises(HealingError):
            self.agent.run({})

    def test_bad_failure_type_raises_healing_error(self) -> None:
        with self.assertRaises(HealingError):
            self.agent.run({"failure": 123})


class HealingAgentSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = HealingAgent()

    def test_selector_failure_is_healed(self) -> None:
        result = self.agent.run(
            {
                "failure": {
                    "suite": "ui/contact-form",
                    "message": "locator '.toast-success > span' resolved to 0 elements",
                    "locator": ".toast-success > span",
                    "source": '<div role="status"><span>{message}</span></div>',
                }
            }
        )
        self.assertIsInstance(result, HealProposal)
        self.assertEqual(result.kind, "selector")
        self.assertEqual(result.suggested_locator, 'getByRole("status")')
        self.assertGreater(result.confidence, 0.0)

    def test_selector_prefers_testid(self) -> None:
        result = self.agent.run(
            {
                "failure": {
                    "suite": "ui/x",
                    "message": "selector not found",
                    "source": '<button data-testid="submit-btn" role="button">Go</button>',
                }
            }
        )
        self.assertEqual(result.suggested_locator, 'getByTestId("submit-btn")')


class HealingAgentTimingTests(unittest.TestCase):
    def test_timeout_failure_is_healed_as_timing(self) -> None:
        result = HealingAgent().run(
            {"failure": {"suite": "ui/x", "message": "Timeout 5000ms exceeded waiting for element"}}
        )
        self.assertEqual(result.kind, "timing")


class HealingAgentEscalationTests(unittest.TestCase):
    """The safety property — real/ambiguous failures must escalate."""

    def setUp(self) -> None:
        self.agent = HealingAgent()

    def test_functional_status_change_escalates(self) -> None:
        with self.assertRaises(UnhealableTestError):
            self.agent.run(
                {
                    "failure": {
                        "suite": "api/contacts",
                        "message": "expected status 201 but received status 400",
                    }
                }
            )

    def test_ambiguous_failure_escalates(self) -> None:
        with self.assertRaises(UnhealableTestError):
            self.agent.run(
                {"failure": {"suite": "api/x", "message": "something went wrong"}}
            )

    def test_selector_signal_overrides_functional_wording(self) -> None:
        # A toHaveText failure that *also* says the locator resolved to 0 elements
        # is a moved selector, not a content bug — should heal, not escalate.
        result = self.agent.run(
            {
                "failure": {
                    "suite": "ui/contact-form",
                    "message": (
                        "expect(locator).toHaveText: Timed out waiting; "
                        "locator resolved to 0 elements"
                    ),
                    "source": '<div role="status"><span>x</span></div>',
                }
            }
        )
        self.assertEqual(result.kind, "selector")


if __name__ == "__main__":
    unittest.main()
