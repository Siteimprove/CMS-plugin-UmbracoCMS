# Release 1.0.0

The GA version is **1.0.0**. The project owner confirmed successful functional
acceptance on 22 October 2026 and selected GA. Known CMS dependencies and hosting
coverage are recorded in [VALIDATION.md](VALIDATION.md); they are not changed by
this packaging release. CI builds and verifies artifacts; NuGet publication uses
the manually triggered **Publish Umbraco 17 to NuGet** workflow.

## Merge and select the release commit

1. Confirm the final PR validation is green, then merge into `master`.
   Preserve the `umbraco-13` branch and existing v13 NuGet package.
2. Wait for **Umbraco 17 validation** on the resulting `master` commit to succeed.
   Use that merged commit's artifacts for publication. PR artifacts can refer to
   GitHub's temporary test merge commit, so do not tag or publish those by mistake.
3. Record the full merged commit SHA and successful run ID. Download its
   `Siteimprove-Umbraco17-release` artifact:

```sh
gh run download <successful-master-run-id> --repo Siteimprove/CMS-plugin-UmbracoCMS --name Siteimprove-Umbraco17-release --dir release-1.0.0
```

If a manual validation run is needed, use:

```sh
gh workflow run ci.yaml --repo Siteimprove/CMS-plugin-UmbracoCMS --ref master
```

The run must test the same commit selected for publication. Recheck the commit
if another change lands on `master`. No publication step rebuilds the package.

## Verify the bundle

Use Python 3.10 or later from the repository checkout:

```sh
python3 scripts/verify-release-bundle.py release-1.0.0/Siteimprove.Umbraco17.Plugin.1.0.0.customer.zip --require-ci --expected-source-commit <full-merged-commit-sha>
python3 -m zipfile -e release-1.0.0/Siteimprove.Umbraco17.Plugin.1.0.0.customer.zip release-1.0.0/contents
```

Check `release.json`: `version` is `1.0.0`, `release_channel` is `stable`,
`source_worktree_dirty` is `false`, the workflow succeeded, and `source_commit`
and `build_commit` both identify the selected merged commit. The NuGet package's
repository commit must match `build_commit`; the verifier checks this.

The verifier checks ZIP/sidecar and internal checksums, exact contents, package
identity and provenance, and relative guide links. Checksums verify integrity;
obtain artifacts from the trusted repository and confirm the workflow result.
The older `verify-beta-bundle.py` command remains an alias, and historical beta
bundles remain verifiable.

## Publish the same artifacts

1. Create a **draft** GitHub release with a new tag `v1.0.0` targeting the full
   merged commit. Use `docs/releases/1.0.0.md` as the notes. Attach the verified
   customer ZIP, its `.sha256`, and the `.nupkg` extracted from it. Leave
   **Set as a pre-release** unchecked. Verify the draft target and attachments.
2. Open **Actions → Publish Umbraco 17 to NuGet → Run workflow** on `master`.
   Enter the successful validation run ID and exact version. The workflow downloads
   that run's customer bundle, verifies checksums and provenance, and pushes the
   original `.nupkg` using the organization secret `NUGET_ORG_API_KEY`. It does
   not rebuild the package or change the GitHub release. The same dispatch via CLI:

```sh
gh workflow run publish.yaml --repo Siteimprove/CMS-plugin-UmbracoCMS --ref master -f validation_run_id=<successful-master-run-id> -f version=1.0.0
```

   The existing 1.0.0 release was validated by run **39796390400**, source commit
   `5b07ac02e0f0152827a69f284eb05746154e2eab`. Its GitHub release is already
   published. Select that run to push the existing release to NuGet; keep its
   published assets unchanged. Artifact retention still applies. If the artifact
   has expired, stop and recover the exact verified bundle before publishing.

   The secret must allow this repository and NuGet's **Push new packages and
   package versions** operation for `Siteimprove.Umbraco17.Plugin`. A key limited
   to the v13 ID or to new versions of existing packages cannot create the v17 ID.
   On a 403, ask a Siteimprove NuGet account admin (Caíque or Andrew) to check
   package scope, new-package permission and expiration. An admin can alternatively
   upload this exact package once, then allow the key to push later versions.
   Never copy the key into source, logs, release notes or command history.

   Alternatively, sign in to [NuGet.org](https://www.nuget.org/packages/manage/upload),
   select **Upload**, choose that same `.nupkg`, review its metadata and submit.
   This option does not require a local .NET SDK or an API key.

3. Confirm NuGet lists stable `1.0.0` and a clean Umbraco 17 project can restore
   it from NuGet.org. NuGet processing/indexing can take time. If the package
   already exists, inspect its identity and checksum; do not overwrite or silently
   skip a different upload. The workflow deliberately fails on duplicates rather
   than using `--skip-duplicate`; inspect the existing NuGet package before retrying.
4. Publish the GitHub draft as the latest stable release, unless already published.
   Keep the exact assets and package checksum with the release record.
5. Follow [Marketplace consolidation](MARKETPLACE.md), validate the metadata and
   verify the v13/v17 installation choices after synchronization.

The repository is now `Siteimprove/CMS-plugin-UmbracoCMS`. Historical bundles and
the 1.0.0 package retain the previous repository URL; the verifier accepts that
rename while checking the run ID and source/build commits. Refresh package
project/repository URLs before the next package version; do not rebuild 1.0.0
just to update metadata. GitHub's rename redirects preserve existing links.

## Future versions

Update `Directory.Build.props`, the backoffice manifest and all versioned relative
JavaScript imports together. Update the preview injector test's expected asset
version, guide versions/links and add matching release
notes, then run the full
validation workflow. The bundle tools accept stable `X.Y.Z` and beta
`X.Y.Z-beta.N` versions and record their channel. Any change to code or packaging
requires new validated artifacts. Retain the prior package for rollback.
