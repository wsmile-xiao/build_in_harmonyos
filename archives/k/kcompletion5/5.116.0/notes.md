# KCompletion 5.116.0 HarmonyOS PC port

## Package

KCompletion is the KDE Frameworks 5 Qt widget completion library. This recipe
builds `KF5Completion` from the official KDE 5.116.0 source archive for
HarmonyOS PC aarch64 using Qt 5.

## Dependencies

- `qt5-qtbase/5.15.2.2` provides Qt5 Widgets and QtTest.
- `kconfig5/5.116.0` provides the KConfig APIs linked by KCompletion.
- `kwidgetsaddons5/5.116.0` provides the KCursor APIs linked by KCompletion.
- `ecm/6.26.0` provides KDE Extra CMake Modules at build time.

All four references were checked with `conan download --only-recipe -r=ohpcd`
before port work began.

## HarmonyOS build adaptations

- Force `QT_MAJOR_VERSION=5`; ECM 6 otherwise defaults new Frameworks projects
  to Qt6.
- Set `KF_IGNORE_PLATFORM_CHECK=TRUE` because KDE's platform list does not yet
  include HarmonyOS.
- Turn off the optional Qt Designer plugin; the published Qt5 package does not
  provide Qt5UiPlugin.
- Add HarmonyOS SONAME flags so the shared library has a relocatable ELF
  `DT_SONAME`.
- Provide Qt5 moc/rcc/uic paths and ECM module paths from Conan package folders.
- Add the Qt5 and KDE dependency package CMake directories explicitly. The KDE
  Qt module config calls `find_dependency(Qt5Xml)`, while the imported KConfig
  and KWidgetsAddons configs are not part of the generated Qt umbrella file.
- Copy Qt's `mkspecs/linux-clang` and `mkspecs/common` into the adjacent Conan
  build cache path expected by the published Qt module config files.
- Guard the upstream translation catalog install call with the generated
  portability patch. Builds with Qt5LinguistTools keep PO installation; the
  HarmonyOS build can configure when that optional tool is absent.
- Run all registered upstream CTest cases under Qt's offscreen platform.

## Test coverage

The upstream CMake project declares four CTest autotests. It also builds three
manual GUI test applications under `tests/`; these are interactive applications
and are not registered as automated tests. The Conan consumer test runs on the
HarmonyOS device, checks its real system name and architecture, creates a Qt
Widgets application and KLineEdit, sends keyboard input through QtTest, and
checks the actual completed text.

## Build and test results

HarmonyOS 6.0 aarch64 `conan create` built the shared library and ran its
consumer test successfully. All four upstream CTest programs passed with no
exclusions. The consumer test also ran directly and observed completion of
`Har` to `HarmonyOS`. Exact per-program results and test-environment notes are
in `reports/test-report.md`.
---

**编译结束**: 2026-10-06 13:32
**最终状态**: built
