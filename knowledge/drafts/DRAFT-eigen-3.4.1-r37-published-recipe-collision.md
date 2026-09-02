# Draft: eigen 3.4.1 same-version R37 collision

> Source event: `eigen/3.4.1` OHOS shadow CI on 2026-08-28.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

`eigen/3.4.1` was already published in the Conan registry. A first shadow CI
attempt changed the same-version recipe and failed before build/test at L0:

```text
eigen/3.4.1 already published with different recipe (R37)
version_not_incremented
```

For a package that is already present remotely, same-version edits to
`conanfile.py` or `conandata.yml` produce a new recipe revision. The registry
gate treats that as an immutable-version collision, even if the edit only looks
like a minor preflight or test convenience change.

## Recommended handling

When R37 reports a published same-version recipe collision:

1. Decide whether the package recipe really needs to change.
2. If only metadata, notes, or `test_package` evidence are being added, restore
   `conanfile.py` and `conandata.yml` byte-for-byte to the published archive
   entry and rerun the single-package gate.
3. If a packaging or source fix truly requires a recipe change, create a
   suffix version such as `3.4.1.1` and update the archive directory,
   `version`, `MANIFEST.yml`, notes, and references together.
4. Keep the failed L0 run in notes as evidence, because it explains why the
   final PR intentionally avoids same-version recipe edits.

Do not use a local Conan cache hit as proof that the PR will pass. Use a fresh
shadow CI or isolated `CONAN_HOME` so the R37 remote check is visible.

## Evidence

- Failed runner:
  `/storage/Users/currentUser/ohos-test-runs/codex-eigen-eigen-eigen-3.4.1-C0DX-shadow-r1-20260828-100021-42976`
- Failed shadow run:
  `/storage/Users/currentUser/ohpc-ci-shadow/runs/20260828T020023Z-1a9b11bd4b-43039`
- Root cause: the r1 input contained a local `conanfile.py` change.
- Fixed runner:
  `/storage/Users/currentUser/ohos-test-runs/codex-eigen-eigen-eigen-3.4.1-C0DX-shadow-r2-20260828-100610-44905`
- Fixed shadow run:
  `/storage/Users/currentUser/ohpc-ci-shadow/runs/20260828T020611Z-48f48aced7-44968`
- Fixed input commit: `48f48aced7`
- Fixed result: `L0_RESULT=pass: all checks passed`; `Total: 1`,
  `Success: 1`, `Failed: 0`.

## Relation to existing knowledge

Many package notes mention R37 suffix versions. This draft records the
additional same-version path used for eigen: keep the already-published recipe
unchanged and improve only consumer validation and evidence. It is useful for
header-only or already-usable packages where a recipe bump would be unnecessary
noise.

## Boundaries

This is not a recommendation to avoid version bumps when the recipe really has
to change. It only applies when the published recipe can stay intact and the PR
is adding validation, documentation, or directly related knowledge drafts.
