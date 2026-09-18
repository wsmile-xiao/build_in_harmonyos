# kglobalaccel 6.26.0 notes

## Scope

First HarmonyOS PC (aarch64 / OHOS) adaptation of KDE Frameworks 6
kglobalaccel 6.26.0 (`libKF6GlobalAccel.so`, `KF6::GlobalAccel`).
Upstream tarball: `kglobalaccel-6.26.0.tar.xz`,
sha256 `3f19d22d143577e5ddcc883170fe19a56f8f65766e41c4f9c011c4dfbde17a61`.

kglobalaccel is **tier 1**: upstream `.kde-ci.yml` declares exactly one
dependency (`frameworks/extra-cmake-modules: '@same'`) and the sources include
no KF6 headers at all. Build-time dependencies are ECM + Qt6 + the poqm
translation tooling.

## Dependencies (all verified consumable before starting, R36)

| dep | source of truth | verified |
|---|---|---|
| ecm/6.26.0 (extra-cmake-modules) | upstream `find_package(ECM 6.26.0 NO_MODULE)` (CMakeLists.txt:9) | `conan download -r=ohpcd` EXIT=0 |
| qtbase-sql-dbus/6.11.1 | provides Qt6::Core/Gui/Widgets/Test/DBus (qtbase has `FEATURE_dbus=OFF`) | EXIT=0 |
| qt6linguisttools/6.11.1 | `ecm_install_po_files_as_qm(poqm)` -> `find_package(Qt6 COMPONENTS LinguistTools CONFIG REQUIRED)` | EXIT=0 |
| qtdeclarative/6.11.1 | `tests/CMakeLists.txt:1 find_package(Qt6Qml REQUIRED)` | EXIT=0 |
| qtbase/6.11.1, qtshadertools/6.11.1, qttools/6.11.1.1, dbus/1.14.10, expat/2.8.2 | transitive | EXIT=0 |

No dependency had to be adapted or published first.

## Upstream version baseline (6.26.0)

- `cmake_minimum_required(VERSION 3.29)` — local cmake 4.1.2 satisfies it.
- `KF_VERSION`/`KF_DEP_VERSION` = 6.26.0; `REQUIRED_QT_VERSION` = 6.9.0 —
  `qtbase*/6.11.1` satisfies it.
- `find_package(Qt6 ... CONFIG REQUIRED DBus Gui Widgets)` and, because
  `Qt6Gui_VERSION >= 6.10.0`, `find_package(Qt6GuiPrivate REQUIRED NO_MODULE)`.
- `option(WITH_X11 "Build with X11 support" ON)` — default ON.
- `ecm_install_po_files_as_qm(poqm)` with 102 translation catalogs.
- `if(BUILD_TESTING) find_package(Qt6 ... Test); add_subdirectory(tests)`.
- `KF6GlobalAccelConfig.cmake.in` re-declares
  `find_dependency(Qt6DBus)` + `find_dependency(Qt6Widgets)` for consumers.
- Release notes for 6.26.0 list no KGlobalAccel entry; "Frameworks 6.26.0
  requires Qt 6.9.0" is the only relevant statement.

## Adaptations (recipe layer only — zero source patches)

1. `KF_IGNORE_PLATFORM_CHECK=TRUE` — ECM's `KDEMetaInfoPlatformCheck` reads
   `metainfo.yaml` (platforms: Linux, FreeBSD) and calls `message(FATAL_ERROR)`
   on HarmonyOS.
2. `WITH_X11=OFF` — upstream defaults it ON and `src/kglobalaccel.cpp:25-26`
   then includes `<private/qtx11extras_p.h>`; the OHOS Qt builds ship
   `FEATURE_xcb/xlib=OFF` and no such private header.
3. `qtbase-sql-dbus/6.11.1` as the Qt provider — the only OHOS package that
   ships `lib/cmake/Qt6DBus` + `libQt6DBus.so`.
4. `ECM_MODULE_PATH` set explicitly (CMakeDeps' generated `ECMConfig.cmake`
   does not propagate it) and a hand-written `conan_cmakedeps_paths.cmake`
   (qtbase uses `cmake_find_mode=none`), with qtbase-sql-dbus ordered first.
5. `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` lists every Qt package folder so
   `find_package(Qt6 COMPONENTS LinguistTools)` can resolve a module that
   lives in a different Conan package than the Qt6 base config.
6. Build/test runtime environment: prepend `/system/lib64` and the OHOS SDK
   `llvm/lib` to `LD_LIBRARY_PATH` (kconfig/kcrash 6.26.0 precedent) so the
   `qtpaths`/`lconvert` host tools and the poqm step resolve compatible
   `libc++_shared.so`.
7. `BUILD_TESTING=ON` so the upstream test entry point is compiled.
8. `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"` — required so
   CMake honours `VERSION`/`SOVERSION` on HarmonyOS (see error #5 below).
   Without it the package ships an unversioned `.so` with no `DT_SONAME`.

## Errors encountered during the adaptation (first error -> root cause -> fix)

| # | First error (verbatim) | Root cause | Fix | Re-verification |
|---|---|---|---|---|
| 1 | `CMake Error at .../ECM/kde-modules/KDEMetaInfoPlatformCheck.cmake:79 (message): Your current platform 'HarmonyOS' is not supported. The list of supported platorms is 'Linux;FreeBSD'` (call stack `KDEFrameworkCompilerSettings.cmake:70 -> CMakeLists.txt:18`) | ECM enforces the platform allowlist from metainfo.yaml; OHOS is not listed | `tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"` | attempt 2 configures past the check |
| 2 | `CMake Error at .../ECMPoQmTools.cmake:155 (find_package): Expected Config file at ".../qtbasaa5545cd5ea92/p/lib/cmake/Qt6LinguistTools/Qt6LinguistToolsConfig.cmake" does NOT exist` (call stack `ECMPoQmTools.cmake:249 -> CMakeLists.txt:54`) | `find_package(Qt6 COMPONENTS LinguistTools)` resolves modules relative to the already-found `Qt6_DIR` (qtbase-sql-dbus package folder); qt6linguisttools lives in a separate Conan package | `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` = all Qt package folders (+ `Qt6LinguistTools_DIR` fallback) | attempt 3: poqm step passes, build proceeds to 94% |
| 3 | `/…/src/kglobalaccel.cpp:26:10: fatal error: 'private/qtx11extras_p.h' file not found` | `WITH_X11` defaults ON; no X11/QtGui-private-X11 header in the OHOS Qt builds | `tc.variables["WITH_X11"] = "OFF"` | attempt 4: `libKF6GlobalAccel.so` + `kglobalacceltest` link at 100% |
| 4 | `CMake Error at CMakeLists.txt:5 (find_package): By not providing "Findkglobalaccel.cmake" … Could not find a package configuration file provided by "kglobalaccel"` | The auto-generated `conan-init` test_package looked for `kglobalaccelConfig.cmake`; the real package is `KF6GlobalAccel` with `cmake_find_mode=none` | rewrote `test_package/{CMakeLists.txt,conanfile.py,test.cpp}` against `KF6GlobalAccel`/`KF6::GlobalAccel` | attempt 5: `conan create` EXIT=0, test_package 1/1 Passed |
| 5 | `[fail] L5a: libKF6GlobalAccel.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址` + `[fail] L5c: 1 个 .cmake 文件含 IMPORTED_NO_SONAME TRUE` (W3 local CI, L5 gate) | Conan maps `settings.os=OHOS` to `CMAKE_SYSTEM_NAME=HarmonyOS`; CMake has no `Platform/HarmonyOS.cmake` (its `Platform/OHOS.cmake` is only selected for `CMAKE_SYSTEM_NAME=OHOS` and inherits the Linux SONAME rule). The generic fallback leaves `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` unset, so CMake ignores the upstream `VERSION`/`SOVERSION` target properties and links an unversioned `.so` with no `DT_SONAME` | recipe `generate()` now sets `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` / `..._CXX_FLAG` = `-Wl,-soname,` (verified minimal reproduction: link line gains `-Wl,-soname,libfoo.so.6`) | attempt 6: package ships `libKF6GlobalAccel.so.6.26.0` + `libKF6GlobalAccel.so.6` symlink, `readelf -d` shows `SONAME: libKF6GlobalAccel.so.6`, `IMPORTED_NO_SONAME` gone, `conan create` EXIT=0 |

## Upstream tests (R51 three-step declaration)

**Step 1 — inventory.** `tests/` contains 3 files (`CMakeLists.txt`,
`kglobalacceltest.cpp`, `kglobalacceltest.qml`). `tests/CMakeLists.txt` only
declares `add_executable(kglobalacceltest …)` + `target_link_libraries(… KF6::GlobalAccel Qt6::Qml Qt6::Test)`;
there is **no `add_test()`**, so the upstream registers **0 automated cases**.

**Step 2 — run (real machine, OHOS PC).** Build performed with the recipe's
own toolchain into `/storage/Users/currentUser/tmp/kglobalaccel-uptest`
(log: `kglobalaccel-6.26.0-adapt/logs/09b-upstream-build.log`, EXIT=0).

```
$ ctest --test-dir <build> -N            -> Total Tests: 0            EXIT=0
$ ctest --test-dir <build> -N --no-tests=error -> Total Tests: 0      EXIT=0
$ cd <build>/bin && QT_QPA_PLATFORM=offscreen timeout 15 ./kglobalacceltest
  QQmlApplicationEngine failed to load component
  file:///…/tests/kglobalacceltest.qml:11:1: module "org.kde.kquickcontrols" is not installed
  EXIT=124        # program reached app.exec(); terminated by timeout, no crash
```
Log: `kglobalaccel-6.26.0-adapt/logs/07-upstream-test-run.log`.

**Step 3 — report.** Total upstream cases **0**, passed **0**, failed **0**,
skipped **0**. The only entry point is a non-asserting GUI/QML executable that
never returns; its QML scene needs `org.kde.kquickcontrols`, which is provided
by kdeclarative — and kdeclarative reverse-depends on kglobalaccel (its 6.26.0
recipe even carries `0001-ohos-disable-kglobalaccel.patch`), so pulling it in to
satisfy the QML scene is impossible (dependency cycle). The executable is
therefore reported as "runs to event loop, no automated assertion" instead of a
passing test.

`test_package` is **not** used as a substitute for upstream statistics; it is
listed separately in the manifest (`test_package: 1/1 ctest passed`, 6 real
assertions — the consumer test fails with a non-zero exit code if any
assertion does not hold).

## Verification

```
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
  ... 100% Built target KF6GlobalAccel / kglobalacceltest
  1/1 Test #1: test_kglobalaccel ................   Passed    0.07 sec
  100% tests passed, 0 tests failed out of 1
EXIT=0
```
Log: `kglobalaccel-6.26.0-adapt/logs/06-conan-create-attempt5.log`.

Package contents (log `08-package-content.log`): `include/KF6/KGlobalAccel/*.h`,
`lib/libKF6GlobalAccel.so`, `lib/cmake/KF6GlobalAccel/*.cmake`,
`share/dbus-1/interfaces/kf6_org.kde.KGlobalAccel.xml` (+ Component.xml),
`share/locale/*/LC_MESSAGES/kglobalaccel6_qt.qm` (102 catalogs),
`share/qlogging-categories6/kglobalaccel.*`. **No `bin/` directory** → plain
library package, no `commands.json` (R38).

`readelf -d libKF6GlobalAccel.so` → NEEDED: libQt6Widgets/Gui/DBus/Core.so.6,
libc++_shared.so, libc.so; `FLAGS: BIND_NOW` (no system-name library, R26 not
applicable).

## Caveats

- Runtime needs a session D-Bus for actual shortcut registration; the library
  itself degrades gracefully without one (the consumer test exercises the API
  and observes `setShortcut()` returning without crashing).
- The X11 code path is compiled out (`WITH_X11=OFF`); on HarmonyOS the
  supported shortcut backend is the Plasma/Wayland-style global shortcut
  service, not X11 grabs.
---

**编译结束**: 2026-09-15 16:34
**最终状态**: built
