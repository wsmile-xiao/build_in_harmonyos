# safekeep 1.5.1 Build Notes

Date: 2026-08-01

## Summary

SafeKeep 1.5.1 is a Python 3 command-line backup manager. The Conan recipe
packages the upstream `safekeep` script as `bin/safekeep` and includes the
upstream `safekeep-test` integration test driver, configuration sample, cron
script, text documentation, and sample backup file under `share/safekeep`.

The SourceForge release links listed by upstream returned HTTP 403 in this build
environment. The recipe therefore uses the GitHub `1.5.1` tag tarball from
codeload, which downloaded successfully with SHA-256:

`c5efcbbdb8e141d6aeac648c4833f935f5982c01f58cd26ff6b35fcc43c609fb`

For restricted CI networks, the same verified archive is committed beside the
recipe as base64 text in `safekeep-1.5.1.tar.gz.b64` and exported through
`exports_sources`. The `source()` step decodes it back to
`safekeep-1.5.1.tar.gz`, validates the decoded archive with the same SHA-256,
and unpacks it before falling back to the upstream codeload URL. The text form
also keeps the PR diff applyable on CI workers that fetch merge requests as
plain `.diff` files that do not carry binary payload data.

## Runtime Notes

The script imports Unix-only modules such as `pwd` and `fcntl`, and it shells out
to system backup tools. The Windows-local test package intentionally avoids
executing the command and verifies the packaged command, version marker, docs,
sample config, and sample backup definition instead.

Runtime use on OpenHarmony requires Python 3 plus external tools such as
`rdiff-backup` and OpenSSH. Snapshot and database backup modes may require
additional utilities.

The upstream command script uses an absolute Python shebang. During packaging it
is rewritten to `#!/usr/bin/env python3` so the OpenHarmony runtime uses the
available Python wrapper from `PATH`.

## Upstream Tests

Upstream provides `safekeep-test`, a Python integration test driver with local
and remote backup modes. The local path creates a temporary backup tree, runs
`safekeep --server`, restores with `rdiff-backup -r now`, and compares MD5
sums. The remote path additionally assumes SSH access, root setup, package
deployment, and target host mutation.

For OHOS, the recipe applies a test-only patch to `safekeep-test`. The patch
keeps the upstream driver structure and changes only the local test harness
needed by the runner:

- uses a local safekeep client emulator for the server/client protocol;
- launches the server from the wrapper directory so OHOS Python subprocess can
  resolve `safekeep --client` without relying on PATH lookup;
- disables the default `nice`/`ionice` adjustments that are unavailable in the
  runner;
- keeps the repository under the test temp root and restores through
  `rdiff-backup restore --at now` with a relative repository path, avoiding
  OHOS parent-directory permission checks under `/storage/Users`.

CI #18961 showed that copying `rdiff-backup/2.2.6` into an OHOS app-cache/TMPDIR
workdir is still not a reliable execution route: HNP Python rejected
`rdiff_backup.C` with `dlopen` `Permission denied`. This is the same
Conan/HMDFS user-path policy limitation documented by the `rdiff-backup`
recipe, not a missing dependency declaration.

The OHOS `test_package` therefore does not count either upstream integration
flow as passed. It validates the packaged safekeep command, config, docs,
sample data, and `safekeep-test` flow markers, then checks the
`rdiff-backup/2.2.6` dependency package statically: console entry point metadata,
entry_points mapping, and the signed `rdiff_backup.C` and
`rdiff_backup._librsync` CPython extension artifacts. The remote flow is still
identified but not executed because it also requires SSH, root setup, package
deployment, and mutable client/server hosts.

## OpenHarmony Validation

- CI #18961 before this fix reached test_package and failed only when
  `rdiff-backup` imported its CPython extension from the copied app-cache
  runtime path: `ImportError: ... rdiff_backup/C.cpython-312-aarch64-linux-ohos.so:
  Permission denied`.
- The corrected OHOS test route avoids this platform load-policy oracle and
  performs signed-artifact checks for the `rdiff-backup` dependency instead.
- upstream integration result in CI: `0/2`; local and remote flows are
  identified but not counted as passed under the current runner constraints.
