# kitemviews 6.26.0.1 notes

## Scope

This package is part of the KF6 6.26 baseline (task #6323, dependency chain:
extra-cmake-modules 6.26.0 + qtbase 6.11.1). It updates the existing
HarmonyOS PC recipe from 6.18.0 to KDE Frameworks 6.26.0.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotest during Conan build.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.
- ECM 6.26 KDEInstallDirs6 runs the qtbase `qtpaths` host tool during
  configure; the sandbox LD_LIBRARY_PATH contains an incompatible
  libc++_shared.so which shadows the compatible one, so `/system/lib64` and
  the qtbase lib dir are prepended (kconfig 6.26.0 / bluez-qt 6.28.0
  precedent).

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `e76cc9d7561d0aae22b07a77552fbcddf61c8066bac5cfac9958ac065b617e74`.
- The po/qm patch was verified to apply cleanly against the unpacked 6.26.0
  source with patch_ng (the same engine conan uses); the only upstream change
  near the patch context is the Qt deprecation version line (6.9/6.10 -> 6.11).

OHOS `conan create` verification passed on 2026-09-05 for the base 6.26.0
adaptation. The 6.26.0.1 rebuild — DT_SONAME toolchain flags added in
`conanfile.py` (`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG`) so consumers record
the bare soname instead of an absolute build path — passed on 2026-09-30.

- Runner log: `~/tmp/kitemviews-create-r1.log` (local W3 run).
- Full package reference:
  `kitemviews/6.26.0.1#32a9de775472f1cfe4eff373321d73fc:57ffd8c720a5bfee7e8827990cd6550a49181c1b`.
- Upstream test targets: 4/4 compiled. The only CTest-registered case passed
  1/1 (kitemviews-klistwidgetsearchlinetest); the 3 `tests/` targets are
  interactive GUI demos, never registered by upstream (see "Test counting
  convention" below), and each launched under offscreen QPA (rc=124).
- Conan `test_package`: 1/1 passed.
- Runner results: L0 pass, L1 pass, L4 pass, L5 pass; L2 skip: no bin/ dir
  (library only).

## Test counting convention (rule4 review fix, 2026-10-02)

Upstream ships **4** test targets in `kitemviews-6.26.0.tar.xz`; this is the
counting convention used by the PR-review side (test targets / test source
files), and the declaration was raised from 1 to 4 to match it:

| Target | Directory | CTest-registered upstream | Verified this round |
|---|---|---|---|
| `kitemviews-klistwidgetsearchlinetest` | `autotests/` | yes (1 case) | 1/1 passed |
| `kcategorizedviewtest` | `tests/` | no | compiled; offscreen start rc=124 |
| `ktreewidgetsearchlinetest` | `tests/` | no | compiled; offscreen start rc=124 |
| `kwidgetitemdelegatetest` | `tests/` | no | compiled; offscreen start rc=124 |

- `tests/CMakeLists.txt` calls `ecm_mark_as_test` for its 3 targets, but ECM's
  `ecm_mark_as_test` never calls `add_test` (it only affects the build when
  `BUILD_TESTING` is OFF), so upstream exposes exactly 1 automatic case:
  measured `build/Release/tests/CTestTestfile.cmake` is empty and `ctest -N`
  prints `Total Tests: 1`.
- The 3 `tests/` targets are interactive GUI demos (`main()` -> `show()` /
  `dialog.exec()`), carry no programmatic assertions, and were never part of
  upstream CTest.
- The earlier archive recorded upstream N=1 (counting only the CTest-registered
  case) and thus under-counted the `tests/` directory. This note is the
  corrected record.

---

**编译结束**: 2026-09-30 20:45
**最终状态**: built
