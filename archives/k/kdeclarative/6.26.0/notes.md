# kdeclarative 6.26.0 notes

## Scope

KDE Frameworks 6 declarative bindings framework (QML integration layer), part
of the KF 6.26 baseline chain. Ships the KF6CalendarEvents C++ library, the
kquickcontrols / kquickcontrolsaddons / draganddrop / graphicaleffects QML
plugin modules and C++ helpers backing QML components (quickaddons).

## Upstream

- Source: https://download.kde.org/stable/frameworks/6.26/kdeclarative-6.26.0.tar.xz
- SHA256: 9a464e560e436cd3a626ca6aab894f414c6212d2de8b9c5a8eda33be213e00d8
- License: LGPL-2.0-or-later
- Build system: CMake (ECM / KF6), Qt6 Qml/Quick based.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` — OHOS is not in the KDE platform allowlist.
- `KF_SKIP_PO_PROCESSING=ON` — Qt6LinguistTools not published (same as all
  KF6 packages in this repo).
- `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON` — kdoctools not published.
- `BUILD_TESTING=ON` — upstream test target built during the package build
  (see "Upstream test execution").
- `CMAKE_BUILD_PARALLEL_LEVEL=1` — HMDFS refuses make jobserver fifo creation
  (EPERM); serial make (same as karchive/kconfig precedent).
- `patches/0001-ohos-disable-kglobalaccel.patch` — the generic Linux branch of
  the root CMakeLists requires KF6GlobalAccel; kglobalaccel is not published
  in the ohpcd registry and OHOS has no desktop global-shortcut registry, so
  HAVE_KGLOBALACCEL is forced FALSE. The guard already exists upstream
  (ANDROID/IOS use it): keysequencehelper.cpp / keysequencevalidator.cpp
  compile without KGlobalAccel includes and kquickcontrolsprivate drops the
  KF6::GlobalAccel link. No stub code, no behaviour change beyond the
  optional accelerator integration being compiled out.
- `patches/0002-lower-ecm-and-kf-dep-version.patch` — KF_DEP_VERSION lowered
  6.26.0 -> 6.19.0. The published ohpcd KF6 deps
  (kconfig/kcoreaddons/ki18n/kguiaddons/kwidgetsaddons) are consumed at their
  published 6.26.0 versions, all >= the lowered floor.
- ECM 6.26 `KDEInstallDirs6` runs the qtbase `qtpaths` host tool during
  configure (`ecm_query_qt`); `/system/lib64` and the OHOS SDK llvm lib dir
  are prepended to `LD_LIBRARY_PATH` so the compatible `libc++_shared.so`
  wins over the sandbox bundle copy (kconfig 6.26.0 / kpackage 6.26.0
  precedent).
- The qtbase/qtdeclarative/KF6 packages in this repo are published with
  `cmake_find_mode=none`, so the recipe generates a
  `conan_cmakedeps_paths.cmake` prefix/module layer and injects it via
  `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` (same approach as kconfig/kwidgetsaddons
  6.26.0).

## Dependencies (published ohpcd refs)

- qtbase/6.11.1, qtdeclarative/6.11.1 (Qt6Qml/Qt6Quick), qtshadertools/6.11.1
  (Qt6Quick links Qt6::ShaderTools; the qtbase package does not ship it)
- kconfig/6.26.0, kcoreaddons/6.26.0, ki18n/6.26.0, kguiaddons/6.26.0,
  kwidgetsaddons/6.26.0
- ecm/6.26.0 (tool_requires)

## Upstream test execution (measured)

Upstream `tests/CMakeLists.txt` registers exactly ONE test target:
`qimageitemtest` (add_executable + ecm_mark_as_test, Qt6::Quick + Qt6::Test).
There is no `add_test()` anywhere in the upstream build system of 6.26.0, so
the true upstream CTest registration count is N=0; the single registered test
target is an interactive manual GUI test (`main()` does `view.show()` +
`app.exec()`, the accompanying qimageitemtest.qml is a human-driven
fillMode/isNull inspection).

Verification performed inside the package build (BUILD_TESTING=ON):

1. The test target is BUILT (proves the Qt6Quick/Qt6Test-linked test compiles
   and links against the freshly built QML modules).
2. The executable is launched offscreen (`QT_QPA_PLATFORM=offscreen`) under
   `timeout 10`: exit code 124 (timeout killed the running GUI event loop)
   is the expected healthy outcome on a headless builder; any other non-zero
   code (segfault/abort/missing QML import) would fail the build. Observed:
   exit 124, clean startup, no warnings beyond the usual Qt font-directory
   notice.

## Consumer test (test_package)

`test_package/test_kdeclarative.cpp` exercises the packaged
KF6CalendarEvents library end to end:

- `kdeclarative_version.h` pins the packaged release (6.26.0 / 6 / 26 / 0);
- `CalendarEventsPlugin` — the abstract interface consumers implement — is
  subclassed with a Q_OBJECT (moc/AUTOMOC) and the
  `loadEventsForDateRange` pure virtual is overridden (vtable + moc linkage
  against the installed library);
- `CalendarEvents::EventData` value type: all accessors (uid/title/
  description/start/end/isAllDay/isMinor/type/eventColor) round-trip, and
  QSharedData copy-on-write semantics are verified (mutation of a copy does
  not affect the original);
- the binary runs for real (`self.run`), executed both through CTest
  (1/1 passed) and directly (PASS line with the live uid/title values).

## Package contents

- `lib/libKF6CalendarEvents.so` (cpp_info.libs)
- `lib/qml/org/kde/{kquickcontrols,kquickcontrolsaddons,draganddrop,graphicaleffects}`
  QML plugin modules + qmldir/qmltypes (consumed through QML2_IMPORT_PATH,
  exported via runenv_info)
- `include/KF6/KDeclarative/{kdeclarative_version.h, CalendarEvents/...}`
- `lib/cmake/KF6Declarative/` Config files (cmake_find_mode=none + builddirs,
  consumers discover them through CMAKE_PREFIX_PATH)

## R26 / commands.json

Library package (shared KF6 library + QML plugins, no standalone CLI tools):
commands.json not required.
---

**编译结束**: 2026-09-10 01:22
**最终状态**: built
