"""Publication must use the exact package from a successful master validation."""

import copy
import importlib.util
from pathlib import Path
import unittest

import test_release_bundle as fixtures

spec = importlib.util.spec_from_file_location(
    "nuget_publication", Path(__file__).resolve().parents[2] / "scripts/prepare-nuget-publication.py")
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)

REPOSITORY = "Siteimprove/CMS-plugin-UmbracoCMS"
RUN = {
    "id": 123, "repository": {"id": 42, "full_name": REPOSITORY},
    "head_repository": {"id": 42}, "path": ".github/workflows/ci.yaml",
    "head_branch": "master", "event": "push", "status": "completed",
    "conclusion": "success", "head_sha": fixtures.COMMIT,
}


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.StableBundleVerificationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.write_bundle()
        self.directory = self.fixture.bundle.parent
        self.output = self.directory / "publication"

    def prepare(self, run=None, version="1.0.0"):
        return publication.prepare(run or RUN, REPOSITORY, "123", version, self.directory, self.output)

    def test_original_package_bytes_and_renamed_repository(self):
        package, release = self.prepare()
        self.assertEqual(self.fixture.files[self.fixture.package], package.read_bytes())
        self.assertEqual(fixtures.COMMIT, release["build_commit"])

    def test_invalid_validation_runs(self):
        for field, value in (
            ("id", 456), ("repository", {"id": 43, "full_name": "another/repo"}),
            ("head_repository", {"id": 43}), ("path", ".github/workflows/publish.yaml"),
            ("head_branch", "feature"), ("event", "pull_request"),
            ("status", "in_progress"), ("conclusion", "failure"), ("head_sha", "bad"),
        ):
            with self.subTest(field=field):
                run = copy.deepcopy(RUN)
                run[field] = value
                with self.assertRaises(ValueError):
                    self.prepare(run)
                self.assertFalse(self.output.exists())

    def test_manual_master_run(self):
        run = dict(RUN, event="workflow_dispatch")
        self.prepare(run)

    def test_bundle_from_another_run_or_owner(self):
        for url in (
            "https://github.com/Siteimprove/CMS-plugin-UmbracoCMS/actions/runs/456",
            "https://github.com/another/CMS-plugin-UmbracoCMS/actions/runs/123",
        ):
            with self.subTest(url=url):
                self.fixture.release["validation_workflow"] = url
                self.fixture.write_bundle()
                with self.assertRaisesRegex(ValueError, "selected validation run"):
                    self.prepare()
                self.assertFalse(self.output.exists())

    def test_pr_merge_package_is_rejected(self):
        self.fixture.release["build_commit"] = "b" * 40
        package_files = fixtures.archive_files(self.fixture.files[self.fixture.package])
        manifest = f"{fixtures.PACKAGE_ID}.nuspec"
        package_files[manifest] = package_files[manifest].replace(fixtures.COMMIT.encode(), b"b" * 40)
        self.fixture.files[self.fixture.package] = fixtures.zipped(package_files)
        self.fixture.write_bundle()
        with self.assertRaisesRegex(ValueError, "build commit"):
            self.prepare()

    def test_corrupt_bundle_cannot_produce_package(self):
        self.fixture.bundle.write_bytes(self.fixture.bundle.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_wrong_requested_version_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            self.prepare(version="1.0.1")
        self.assertFalse(self.output.exists())

    def test_unsafe_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Expected a stable"):
            self.prepare(version="../1.0.0")


if __name__ == "__main__":
    unittest.main()
