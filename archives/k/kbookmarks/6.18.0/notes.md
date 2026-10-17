# kbookmarks 6.18.0 notes

## Scope

This package is part of the KF 6.18 baseline. It adds a mainline-ready
`kbookmarks/6.18.0` package directory without modifying other KF package
recipes.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- Runtime/build dependencies use the current local KF baseline:
  `kconfig/6.18.0`, `kcoreaddons/6.18.0`, and `kwidgetsaddons/6.18.0`.

## Verification

Initial local checks:

- Upstream source SHA256 verified on the OHOS runner:
  `41a845ffd9effb8d942d04d76fc3a58b0bf23d3fd36aeba21c89ab9eb0fc4f85`.
- No source patch is required for the 6.18.0 OHOS baseline.

OHOS `conan create` verification passed on 2026-08-20.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kbookmarks-r2.log`.
- Full package reference: `kbookmarks/6.18.0#1d9acd4179a5581b1e3fa17c1fbff918:6e294d968be8fb57babbb74fe58dd5a9798541f1#7a18ccdc47a17954981ced8200ee0d65`.
- Runner results: L0 pass, L1 pass, L5 pass; L2 skip: no bin/ dir; L4 pass.
- Upstream CTest passed 1/1: `kbookmarktest`.
- Upstream manual UI executable `kbookmarkdialogtest` was built with
  `BUILD_TESTING=ON` but was not executed: upstream marks it with
  `ecm_mark_as_test()` and does not register it as a CTest test; it is a
  manual/interactive widget probe.
- The AppStream metadata check was not set up because `appstreamcli` is not
  available as a host tool on the current OHOS runner.
- Conan `test_package` passed 1/1 with a `KBookmarkManager` consumer smoke that
  adds a bookmark, saves the file, and finds the bookmark by address.
