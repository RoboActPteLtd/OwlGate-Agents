"""Tests for the TestCatalogue source->suite mapping."""

from __future__ import annotations

import unittest
from pathlib import Path

from owlgate_agents.catalogue import TestCatalogue
from owlgate_agents.errors import RiskAssessmentError
from owlgate_agents.models import ChangedFile, SuiteSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CATALOGUE = REPO_ROOT / "catalogues" / "sample-app.json"


def _files(*paths: str) -> list[ChangedFile]:
    return [ChangedFile(p) for p in paths]


class CatalogueConstructionTests(unittest.TestCase):
    def test_empty_catalogue_raises(self) -> None:
        with self.assertRaises(RiskAssessmentError):
            TestCatalogue([])

    def test_duplicate_suite_id_raises(self) -> None:
        dup = SuiteSpec("a", ("x/**",))
        with self.assertRaises(RiskAssessmentError):
            TestCatalogue([dup, SuiteSpec("a", ("y/**",))])

    def test_from_json_string_and_path_agree(self) -> None:
        from_path = TestCatalogue.from_json(SAMPLE_CATALOGUE)
        from_str = TestCatalogue.from_json(SAMPLE_CATALOGUE.read_text("utf-8"))
        self.assertEqual(len(from_path), len(from_str))
        self.assertEqual(
            [s.id for s in from_path.suites], [s.id for s in from_str.suites]
        )

    def test_invalid_json_raises(self) -> None:
        with self.assertRaises(RiskAssessmentError):
            TestCatalogue.from_json("{ not valid json ]")

    def test_from_list_missing_id_raises(self) -> None:
        # A suite dict without the required "id" is an unusable catalogue, not a
        # bare KeyError leaking out of construction.
        with self.assertRaises(RiskAssessmentError):
            TestCatalogue.from_list([{"sources": ["x/**"]}])

    def test_from_json_object_without_suites_raises(self) -> None:
        # A JSON object that is not the documented {"suites": [...]} shape.
        with self.assertRaises(RiskAssessmentError):
            TestCatalogue.from_json('{"not_suites": []}')


class CatalogueQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = TestCatalogue.from_json(SAMPLE_CATALOGUE)

    def test_impacted_by_matches_glob(self) -> None:
        impacted = self.cat.impacted_by(
            _files("src/routes/api/contacts/+server.ts")
        )
        self.assertEqual([s.id for s in impacted], ["api/contacts"])

    def test_impacted_by_matches_multiple(self) -> None:
        impacted = self.cat.impacted_by(
            _files(
                "src/routes/contact/+page.svelte",
                "src/routes/api/contacts/+server.ts",
            )
        )
        self.assertEqual(
            sorted(s.id for s in impacted), ["api/contacts", "ui/contact-form"]
        )

    def test_untested_detects_uncovered(self) -> None:
        gap = self.cat.untested(_files("src/lib/util/format.ts", "README.md"))
        self.assertEqual(set(gap), {"src/lib/util/format.ts", "README.md"})

    def test_covered_file_is_not_untested(self) -> None:
        gap = self.cat.untested(_files("src/routes/api/contacts/+server.ts"))
        self.assertEqual(gap, ())

    def test_severity_is_max_tag(self) -> None:
        # api/contacts is tagged validation(0.8)+api(0.6) -> 0.8
        suite = next(s for s in self.cat.suites if s.id == "api/contacts")
        self.assertAlmostEqual(self.cat.severity(suite), 0.8)

    def test_severity_no_tags_is_zero(self) -> None:
        self.assertEqual(self.cat.severity(SuiteSpec("x", ("a/**",))), 0.0)


if __name__ == "__main__":
    unittest.main()
