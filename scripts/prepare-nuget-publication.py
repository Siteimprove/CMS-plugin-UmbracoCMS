"""Select the original NuGet package from a successful master validation run."""

import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse

from package_metadata import release_channel
from release_bundle import PACKAGE_ID, archive_files, verify_bundle


def check_run(run: dict, repository: str, run_id: str) -> str:
    if not re.fullmatch(r"[1-9][0-9]*", run_id) or str(run.get("id")) != run_id:
        raise ValueError("Validation run ID does not match the selected run.")
    if run.get("repository", {}).get("full_name", "").lower() != repository.lower():
        raise ValueError("Validation run belongs to another repository.")
    if run.get("head_repository", {}).get("id") != run.get("repository", {}).get("id"):
        raise ValueError("Validation run must originate in this repository.")
    if run.get("path") != ".github/workflows/ci.yaml":
        raise ValueError("Select the Umbraco 17 validation workflow.")
    if run.get("head_branch") != "master" or run.get("event") not in {"push", "workflow_dispatch"}:
        raise ValueError("Select a push or manual validation run on master, not a pull request.")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise ValueError("Validation run must have completed successfully.")
    commit = run.get("head_sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Validation run has no valid commit SHA.")
    return commit


def prepare(run: dict, repository: str, run_id: str, version: str,
            artifacts: Path, output: Path) -> tuple[Path, dict]:
    commit = check_run(run, repository, run_id)
    release_channel(version)
    bundle = artifacts / f"{PACKAGE_ID}.{version}.customer.zip"
    release = verify_bundle(bundle, require_ci=True, expected_source_commit=commit)
    if release["version"] != version or release["build_commit"] != commit:
        raise ValueError("Bundle version and build commit must match the selected version and master run.")
    # Historical bundles retain the repository name used before its rename.
    workflow_path = urlparse(release["validation_workflow"]).path.split("/")
    if workflow_path[-1] != run_id or workflow_path[1].lower() != repository.split("/")[0].lower():
        raise ValueError("Bundle provenance does not identify the selected validation run.")
    package_name = f"{PACKAGE_ID}.{version}.nupkg"
    files = archive_files(bundle.read_bytes())
    output.mkdir(parents=True, exist_ok=True)
    package = output / package_name
    package.write_bytes(files[package_name])
    return package, release


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check-run", "prepare"))
    parser.add_argument("run", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--version")
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run = json.loads(args.run.read_text())
    commit = check_run(run, args.repository, args.run_id)
    print(f"Validated master run {args.run_id}, commit {commit}.")
    if args.command == "check-run":
        return
    if not all((args.version, args.artifacts, args.output)):
        parser.error("prepare requires --version, --artifacts and --output")
    package, release = prepare(run, args.repository, args.run_id, args.version, args.artifacts, args.output)
    summary = (
        f"Package: `{package.name}`\n\n"
        f"Source commit: `{commit}`\n\n"
        f"Validation: https://github.com/{args.repository}/actions/runs/{args.run_id}\n\n"
        f"SHA-256: `{release['package_sha256']}`\n"
    )
    print(summary)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
            stream.write(f"package_path={package.resolve()}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(summary)


if __name__ == "__main__":
    main()
