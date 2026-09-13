# DRAFT: open62541 task and artifact checks must distinguish an SPA 200 from a package hit

> Status: Draft | Updated: 2026-09-10
> Source event: `open62541/1.5.6` task deduplication and CNB artifact preflight

## Task Deduplication

Before creating a new HarmonyOS adaptation branch, inspect both local archive
paths and remote branch names. For this library/version, the existing
`feat/open62541-1.5.6` line already contains the active adaptation work. An
older `fix/open62541-1.5.6` line contains the same library/version task family.
The correct action is to continue the active worktree and not create a third
branch or a second PR.

## Artifact Check

The Conan client query can be blocked by the remote service's system
acceleration policy. That error does not prove that a package is present or
absent:

```text
error:system acceleration policy not enabled
```

The public CNB registry page is a single-page application and may return HTTP
200 for both existing and nonexistent routes. Inspect the embedded package
detail result. For `open62541/1.5.6`, the page returned a package detail
status with `code=404` and no package data, which is evidence that the exact
recipe is not currently published.

## Decision Rule

1. Check local `archives/<letter>/<name>/<version>/` and remote branches.
2. Query Conan when the remote policy permits it.
3. If Conan is blocked, query the exact public registry route and inspect the
   package-detail payload, not only HTTP status.
4. If the exact recipe is absent and the local recipe is the first submission,
   keep the upstream version number.
5. If the exact recipe exists and the recipe content changes, increment the
   Conan version suffix and synchronize directory, branch, manifest, notes, and
   test package.

## Scope

This is a process guard for one-library/one-branch/one-PR submissions. It
prevents both duplicate task creation and an incorrect version bump caused by a
 misleading SPA response.
