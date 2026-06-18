"""Tests for RiskAgent review_targets — flagging the exact function/lines to review."""

from __future__ import annotations

import unittest

from owlgate_agents import RiskAgent, TestCatalogue

CATALOGUE = [
    {"id": "api/login", "sources": ["src/lib/auth.ts"], "tags": ["auth"], "flakiness": 0.0},
    {"id": "ui/home", "sources": ["src/routes/+page.svelte"], "tags": ["ui"], "flakiness": 0.0},
]


def _diff_with_hunk():
    return [
        {
            "path": "src/lib/auth.ts",
            "lines": 2,
            "hunks": [
                {
                    "function": "export function checkCredentials(input: Credentials): boolean {",
                    "start": 15,
                    "lines": 4,
                }
            ],
        }
    ]


class ReviewTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RiskAgent()
        self.cat = TestCatalogue.from_list(CATALOGUE)

    def test_flags_function_and_line_range(self) -> None:
        r = self.agent.run({"diff": _diff_with_hunk(), "catalogue": self.cat})
        self.assertEqual(len(r.review_targets), 1)
        t = r.review_targets[0]
        self.assertEqual(t["file"], "src/lib/auth.ts")
        self.assertIn("checkCredentials", t["function"])
        self.assertEqual(t["lines"], "15-18")

    def test_no_hunks_means_no_targets(self) -> None:
        r = self.agent.run(
            {"diff": [{"path": "src/lib/auth.ts", "lines": 2}], "catalogue": self.cat}
        )
        self.assertEqual(r.review_targets, ())

    def test_only_impacted_files_are_flagged(self) -> None:
        # a hunk in a file covered by NO suite -> not a review target
        diff = [
            {"path": "src/lib/unmapped.ts", "lines": 2,
             "hunks": [{"function": "f()", "start": 1, "lines": 1}]}
        ]
        r = self.agent.run({"diff": diff, "catalogue": self.cat})
        self.assertEqual(r.review_targets, ())

    def test_single_line_range(self) -> None:
        diff = [{"path": "src/lib/auth.ts", "lines": 1,
                 "hunks": [{"function": "g", "start": 7, "lines": 1}]}]
        r = self.agent.run({"diff": diff, "catalogue": self.cat})
        self.assertEqual(r.review_targets[0]["lines"], "7")

    def test_to_dict_includes_review_targets(self) -> None:
        r = self.agent.run({"diff": _diff_with_hunk(), "catalogue": self.cat})
        self.assertIn("review_targets", r.to_dict())


if __name__ == "__main__":
    unittest.main()
