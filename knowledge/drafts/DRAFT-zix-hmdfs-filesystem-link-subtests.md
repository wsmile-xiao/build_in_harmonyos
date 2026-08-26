# DRAFT-zix-hmdfs-filesystem-link-subtests - Scoped link-operation exemptions for filesystem tests

> Contributor: codex | Status: Draft | Updated: 2026-08-25

## Usage

Use this pattern when an upstream filesystem test aborts on HarmonyOS PC because
a hardlink or symlink operation is rejected by the test directory, while the
library's ordinary file, directory, and path helpers should still be tested.

## Symptom

In zix 0.8.1, the first failing shadow CI run after fixing runtime library
lookup reached the upstream Meson suite and failed only this test:

```text
10/24 unit - zix:filesystem   FAIL   killed by signal 6 SIGABRT
Assertion failed: !zix_create_symlink(file_path, link_path)
```

Earlier evidence also showed hardlink creation can return a platform error on
the same class of OHOS/HMDFS-backed paths.

## Root Cause

The test assumed POSIX link creation is always available. On the target runner,
the filesystem can reject link creation with a capability or permission status,
but that does not invalidate all of the filesystem helper behavior. Aborting the
entire test program loses useful coverage for canonical paths, dot segments,
missing files, and cleanup.

## Recommended Solution

Patch only the capability-sensitive subtest:

1. Accept `ZIX_STATUS_BAD_PERMS` for hardlink creation where upstream already
   accepts unsupported or max-link statuses.
2. For symlinks, call the API once and accept success, `ZIX_STATUS_NOT_SUPPORTED`,
   or `ZIX_STATUS_BAD_PERMS`.
3. Run symlink canonical-path comparison only when symlink creation succeeds.
4. Keep the rest of `test_filesystem` enabled.

This preserves the signal from supported filesystem behavior without pretending
that the runner supports every POSIX link operation.

## Verification

The final zix 0.8.1 shadow CI run passed:

```text
Ok:                21
Expected Fail:     3
Fail:              0
```

The `test_package` consumer also ran `zix_consumer_api` and passed.

## Forbidden Approaches

- Do not disable the whole filesystem test program.
- Do not turn the test into an unconditional success.
- Do not change shared runner mount or permission policy from a package recipe.
