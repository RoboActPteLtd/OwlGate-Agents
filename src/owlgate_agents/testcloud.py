"""TestCloudRunner — the real TestRunner that runs suites in UiPath Test Cloud.

Replaces ``ScriptedTestRunner`` for live PRs: it executes a Test Cloud / Test
Manager **test set** (via the Orchestrator Test Automation API), then maps the
per-test-case results back to the catalogue's suites and returns a ``RunResult``.

Design: the HTTP lives behind a small ``TestExecutor`` seam, so the run/mapping
logic is fully unit-tested with a fake executor — no tenant required. The real
executor (:class:`OrchestratorTestExecutor`) is stdlib-only (``urllib``), so the
core package stays dependency-free.

Not wired into the deployed agent yet. To activate (see uipath-agent/README):
1. ensure the OwlGate test set's cases are **automated** in Test Cloud (so they
   produce real pass/fail — Studio step);
2. swap `ScriptedTestRunner` for `TestCloudRunner(OrchestratorTestExecutor(), …)`
   in `main.py` and redeploy.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from typing import Protocol

from owlgate_agents.models import RunResult, TestFailure


class TestExecutor(Protocol):
    """Runs a named test set and reports each test case's status."""

    def run_test_set(self, test_set: str) -> Mapping[str, str]:
        """Return ``{test_case_name: status}`` (status e.g. 'passed' / 'failed')."""
        ...


class TestCloudRunner:
    """A ``TestRunner`` backed by a Test Cloud executor + a suite→test-case map.

    ``suite_to_cases`` maps each catalogue suite id to the Test Manager test case
    name(s) that cover it. A selected suite fails if any of its cases failed.
    """

    def __init__(
        self,
        executor: TestExecutor,
        test_set: str,
        suite_to_cases: Mapping[str, Iterable[str]],
    ) -> None:
        self._executor = executor
        self._test_set = test_set
        self._map: dict[str, tuple[str, ...]] = {
            k: tuple(v) for k, v in suite_to_cases.items()
        }

    def run(self, suites: list[str]) -> RunResult:
        statuses = {k: str(v).lower() for k, v in self._executor.run_test_set(self._test_set).items()}
        passed = 0
        failures: list[TestFailure] = []
        for suite in suites:
            cases = self._map.get(suite, ())
            failed = [c for c in cases if statuses.get(c) == "failed"]
            if failed:
                failures.append(
                    TestFailure(
                        suite=suite,
                        message=f"Test Cloud: {', '.join(failed)} failed",
                    )
                )
            else:
                # No mapped case failed (passed, or no mapping → nothing ran).
                passed += 1
        return RunResult(passed=passed, failed=len(failures), failures=tuple(failures))


class OrchestratorTestExecutor:
    """Run a test set via the Orchestrator Test Automation OData API (stdlib).

    Uses ``UIPATH_URL`` + ``UIPATH_ACCESS_TOKEN`` (injected into coded agents at
    runtime) and ``UIPATH_FOLDER_ID``. The endpoint paths follow UiPath's
    documented Test API; confirm against your tenant before relying on live
    verdicts.
    """

    def __init__(
        self,
        base: str | None = None,
        token: str | None = None,
        folder_id: str | None = None,
        poll_seconds: float = 5.0,
        max_polls: int = 120,
    ) -> None:
        self._base = (base or os.environ["UIPATH_URL"]).rstrip("/")
        self._token = token or os.environ["UIPATH_ACCESS_TOKEN"]
        self._folder = folder_id or os.environ.get("UIPATH_FOLDER_ID", "")
        self._poll = poll_seconds
        self._max = max_polls

    def _req(self, method: str, path: str, query: dict | None = None, body: dict | None = None) -> dict:
        url = f"{self._base}/orchestrator_{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Content-Type", "application/json")
        if self._folder:
            req.add_header("X-UIPATH-OrganizationUnitId", str(self._folder))
        with urllib.request.urlopen(req) as resp:  # noqa: S310 — UiPath base URL
            return json.loads(resp.read() or b"{}")

    def run_test_set(self, test_set: str) -> dict[str, str]:
        found = self._req("GET", "/odata/TestSets", {"$filter": f"Name eq '{test_set}'"})
        items = found.get("value", [])
        if not items:
            raise RuntimeError(f"test set {test_set!r} not found")
        ts_id = items[0]["Id"]

        started = self._req(
            "POST",
            "/odata/TestSetExecutions/UiPath.Server.Configuration.OData.StartTestSetExecution",
            {"testSetId": ts_id},
        )
        ex_id = started.get("value") or started.get("Id")

        detail: dict = {}
        for _ in range(self._max):
            detail = self._req(
                "GET", f"/odata/TestSetExecutions({ex_id})", {"$expand": "TestCaseExecutions"}
            )
            if detail.get("Status") in ("Passed", "Failed", "Cancelled", "Error"):
                break
            time.sleep(self._poll)

        return {
            (tce.get("Name") or str(tce.get("TestCaseId"))): str(tce.get("Status", ""))
            for tce in detail.get("TestCaseExecutions", [])
        }
