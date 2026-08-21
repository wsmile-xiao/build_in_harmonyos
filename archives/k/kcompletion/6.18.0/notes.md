# kcompletion 6.18.0 notes

## Scope

This package is part of the KF 6.18 baseline. It adds a mainline-ready
`kcompletion/6.18.0` package directory without modifying other KF package
recipes.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- Runtime/build dependencies use the current local KF baseline:
  `kcodecs/6.18.0`, `kconfig/6.18.0`, and `kwidgetsaddons/6.18.0`.

## Verification

Initial local checks:

- Upstream source SHA256 verified on the OHOS runner:
  `6d06881ff2ece4c29df5c3cbe3700cb5e3425064686a667e84f06f2a5732a1c5`.
- No source patch is required for the 6.18.0 OHOS baseline.

OHOS `conan create` verification passed on 2026-08-20.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kcompletion-r2.log`.
- Full package reference: `kcompletion/6.18.0#e5caaa557e3c3286ce7b6d810e7a2714:7439463d4c548b2d90fd38ca08eb07c60c21187f#2855b497e94a6ee0e1825a6e577443bc`.
- Runner results: L0 pass, L1 pass, L5 pass; L2 skip: no bin/ dir; L4 pass.
- Upstream CTest passed 5/5: `kcompletioncoretest`,
  `klineedit_unittest`, `kcombobox_unittest`, `ksortablelisttest`, and
  `kemailvalidatortest`.
- Upstream manual UI executables `kcomboboxtest`, `kcompletionuitest`, and
  `klineedittest` were built with `BUILD_TESTING=ON` but were not executed:
  upstream marks them with `ecm_mark_as_test()` and does not register them as
  CTest tests; they are manual/interactive widget probes.
- The AppStream metadata check was not set up because `appstreamcli` is not
  available as a host tool on the current OHOS runner.
- Conan `test_package` passed 1/1 with a `KCompletion` consumer smoke that
  verifies prefix matching via `allMatches()`.
