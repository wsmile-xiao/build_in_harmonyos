# kitemmodels 6.18.0.1 notes

## Scope

Adaptation fix on top of the released `kitemmodels/6.18.0` (R37 suffix `.1`).
The upstream source is unchanged (same tarball / same sha256); only the conan
recipe changes. This package is a **[dependency]** for `kirigami-gallery`
(R36: the fixed dependency must be published before the downstream is built).

Difference from 6.18.0:

- `6.18.0`   built the **core library only**. `Qt6Qml` was optional and
  `qtdeclarative` was not required, so upstream `src/qml` was skipped and the
  package contained **no QML module** (`qmldir` absent).
- `6.18.0.1` adds `qtdeclarative/6.11.1` as a hard requirement, which makes
  `find_package(Qt6Qml)` succeed and upstream `src/CMakeLists.txt`
  (`if (TARGET Qt6::Qml) add_subdirectory(qml)`) configure the QML module.

Why: `kirigami-gallery` `26.04.0` runs
`src/data/contents/ui/MainPage.qml`, which contains
`import org.kde.kitemmodels as KItemModels`. Without the QML module the import
fails at runtime and the application's main page does not work.

## QML module (verified from the package)

- Module URI: **`org.kde.kitemmodels`** (upstream `src/qml/CMakeLists.txt`:
  `ecm_add_qml_module(itemmodelsplugin URI "org.kde.kitemmodels" VERSION 1.0 ...)`).
- Installed path (inside the package): `lib/qml/org/kde/kitemmodels/`
  (`KDE_INSTALL_QMLDIR` defaults to `${LIBDIR}/qml`; no extra copy/package logic
  needed, plain `cmake.install()` packages it).
- Package contents of that dir:

  ```
  lib/qml/org/kde/kitemmodels/qmldir
  lib/qml/org/kde/kitemmodels/libitemmodelsplugin.so
  lib/qml/org/kde/kitemmodels/itemmodelsplugin.qmltypes
  lib/qml/org/kde/kitemmodels/kde-qmlmodule.version   (= 6.18.0)
  ```

- `qmldir`:

  ```
  module org.kde.kitemmodels
  linktarget itemmodelsplugin
  optional plugin itemmodelsplugin
  classname org_kde_kitemmodelsPlugin
  typeinfo itemmodelsplugin.qmltypes
  depends QtCore
  prefer :/qt/qml/org/kde/kitemmodels/
  ```

- Plugin SONAME/NEEDED: `libitemmodelsplugin.so` has
  `RUNPATH $ORIGIN/../../../../lib` and `NEEDED libKF6ItemModels.so.6`
  (resolved inside the same package).
- QML types exported: `KDescendantsProxyModel` (`QML_NAMED_ELEMENT`),
  `KRoleNames`, `KSortFilterProxyModel` (`QML_ELEMENT`), and the foreign
  `KColumnHeadersModel` / `KNumberModel` (`src/qml/types.h`).

## OHOS-specific adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allow-list for OHOS.
- `BUILD_TESTING=ON` builds and runs the upstream CTest autotests.
- `ECM_MODULE_PATH` set manually because the CMakeDeps-generated ECMConfig.cmake
  does not propagate the variable the project's `CMakeLists.txt` relies on.
- `qtbase` **and** `qtdeclarative` both ship complete, relocatable
  `Qt6*Config.cmake` files and set `cmake_find_mode=none`, so CMakeDeps generates
  nothing for them. Both `lib/cmake` dirs are PREPENDed to `CMAKE_PREFIX_PATH`
  (and `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` is set) through the hand-written
  `conan_cmakedeps_paths.cmake`.
- **Qt host tools need the split-package lib dirs on `LD_LIBRARY_PATH`.**
  `qmltyperegistrar`/`qmlcachegen` (in `qtdeclarative/libexec`) have
  `RUNPATH $ORIGIN/../lib` and `NEEDED libQt6Core.so.6` (which lives in
  `qtbase/lib`), so configure/build/install are wrapped in an environment that
  prepends every dependency's `lib`/`bin` (kdeclarative 6.26.0 precedent).
- **OHOS CMake emits no SONAME by default.** Without a SONAME the QML plugin
  recorded a build-tree relative path (`../../bin/libKF6ItemModels.so`) in
  `DT_NEEDED`, which the OHOS loader cannot resolve. The `soname`/`rpath`
  platform flags are restored via a `CMAKE_USER_MAKE_RULES_OVERRIDE` fragment
  (kirigami 6.18.0 precedent); the library is now installed as
  `libKF6ItemModels.so.6.18.0` + `.so.6` + `.so` and the plugin links
  `libKF6ItemModels.so.6`.
- **Installed ELF files are re-signed.** CMake rewrites the RUNPATH of installed
  shared libraries, which invalidates the OHOS build-time `.codesign` section;
  the OHOS loader then refuses to load them ("Permission denied"). `package()`
  re-signs every packaged ELF with `llvm-objcopy --remove-section .codesign` +
  `binary-sign-tool sign -selfSign 1` (kirigami 6.18.0 / kdeclarative 6.26.0
  precedent).
- `package_info()` publishes `QML2_IMPORT_PATH`/`QML_IMPORT_PATH` =
  `<package_folder>/lib/qml` through `runenv_info` so consumers
  (kirigami-gallery / akonadi) can load `org.kde.kitemmodels`.
- Pure library: no `bin/` executables, so **no `commands.json`** (R38).

## Upstream tests (R51 three-step method)

**Step 1 — census.** Source tree `kitemmodels-6.18.0`:

- `autotests/` contains 13 `*.cpp` files; `kselectionproxymodeltestsuite.cpp`
  is a shared helper linked into several tests, not an independent case.
- `ctest -N` registration count in the configured build tree: **12**.

  ```
  1 kcolumnheadersmodeltest          7 knumbermodeltest
  2 kdescendantsproxymodel_smoketest 8 krearrangecolumnsproxymodeltest
  3 kdescendantsproxymodeltest       9 kselectionproxymodeltest
  4 kextracolumnsproxymodeltest     10 krolenames_qml
  5 klinkitemselectionmodeltest     11 ksortfilterproxymodel_qml
  6 kmodelindexproxymappertest      12 kselectionproxymodel_smoketest
  ```

**Step 2 — run.** Executed inside `conan create` (BUILD_TESTING=ON) with
`QT_QPA_PLATFORM=offscreen`, `ctest --output-on-failure --no-tests=error`.

**Step 3 — result.**

| N (upstream, ctest -N) | N' (actually run) | pass | rate |
| --- | --- | --- | --- |
| 12 | 12 | 12 | 100% |

`100% tests passed, 0 tests failed out of 12` (Total Test time 4.18 s).
This includes the two QtQml autotests `krolenames_qml` and
`ksortfilterproxymodel_qml`, which load `org.kde.kitemmodels` through
`QQmlApplicationEngine` — a second, upstream-owned proof that the QML module is
loadable.

Not-run items and why:

- `autotests/kselectionproxymodeltestsuite.cpp` — shared helper source, not a
  test case (no `ecm_add_test` entry).
- `tests/proxymodeltestapp/*` and `tests/rearrangecolumns.cpp` — interactive
  GUI example/tool sources; upstream registers no `add_test()` for the test-app,
  so they are outside the CTest set.

## Verification

Source SHA256 verified:
`887653b1571ad0afd4b836ad2451a42b07657d0eede1a2628e9c69102ce23de1`.

- `conan create` (ohos-aarch64): **PASS** (`EXIT_CODE=0`).
- Upstream CTest: **12/12 passed**.
- `test_package`: **PASS**.
  - R34: calls `KNumberModel` + `KModelIndexProxyMapper` and asserts row count,
    `ValueRole`, index mapping and round-trip.
  - R53: builds a fresh `QQmlEngine`, adds the package's `lib/qml` import path,
    `import org.kde.kitemmodels`, instantiates `KSortFilterProxyModel` over a
    `KNumberModel` source with a `filterRowCallback`, and asserts the filtered
    row count is 5 (odd numbers 1..10). Prints
    `PASS: KItemModels C++ API + QML module org.kde.kitemmodels OK`.

## Downstream impact

- `kitemmodels/6.18.0.1` is a superset of `6.18.0`: same headers, same core
  library ABI (SOVERSION 6), plus the QML module.
- Existing consumers that declare `kitemmodels/6.18.0` are unaffected until they
  opt in to `6.18.0.1`. `kirigami-gallery` needs `6.18.0.1` (and its
  `org.kde.kitemodels`/`org.kde.kitemmodels` import) to work; see R36 — the
  dependency must be published before rebuilding the downstream.
---

**编译结束**: 2026-09-16 23:38
**最终状态**: built
