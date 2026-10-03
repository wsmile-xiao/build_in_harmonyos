#!/usr/bin/env python3
"""Conan recipe for kddockwidgets 2.4.0 (KDAB docking framework) on HarmonyOS PC.

kddockwidgets is KDAB's Qt-based docking framework (GPL-2.0-only OR
GPL-3.0-only). This recipe builds the Qt5 qtwidgets frontend against the OHOS
Qt5 stack (qt5-qtbase/5.15.2.2, the build that ships Core/Gui/Widgets/Test
and the offscreen QPA plugin).

OHOS-specific adaptations (recipe layer only, no source patches):
  - KDDockWidgets_QT6=OFF: upstream defaults to Qt6 since v2.3.0; the OHOS
    registry provides the Qt5 stack, and upstream still fully supports Qt5
    (QT_MIN_VERSION 5.15) — this is a supported configuration, not a fork.
  - KDDockWidgets_FRONTENDS=qtwidgets: the qtquick frontend would require
    Qt5 Quick/QuickControls2 (qt5-qtdeclarative) plus a working scenegraph
    on the OHOS QPA; the qtwidgets frontend is the upstream-primary C++ API
    and keeps the dependency graph minimal. The upstream qtwidgets test
    inventory (tst_qtwidgets + 23 core suites, 24 ctest cases) is built via
    KDDockWidgets_TESTS=ON.
  - KDDockWidgets_EXAMPLES=OFF: GUI demos, not needed for the library.
  - KDDockWidgets_NO_SPDLOG=ON: spdlog/fmt are optional upstream deps
    (QUIET find_package in the regular-build branch); pinning them OFF makes
    the build deterministic and avoids accidental linkage when such packages
    happen to be present in the cache.
  - KDDockWidgets_X11EXTRAS=OFF: X11 extras are Linux-X11-only; OHOS ships
    no X11 (the option's Qt5 branch adds Qt5::X11Extras, absent on OHOS).
  - The native Qt5 cmake config shipped by qt5-qtbase is unusable; CMakeDeps
    regenerates a clean Qt5Config via set_property("qt5-qtbase",
    "cmake_file_name", "Qt5") (kglobalaccel/attica5 precedent), so
    find_package(Qt5 5.15 NO_MODULE REQUIRED COMPONENTS Widgets Test)
    resolves for both the library build and the consumer.
  - CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE point at qt5-qtbase bin/
    {moc,rcc,uic}: the library uses Q_OBJECT classes and the tst_qtwidgets
    suite ships mainwindow.ui (tests/CMakeLists.txt enables AUTOUIC).
  - SONAME: HarmonyOS is not mapped to the Linux CMake platform, so
    CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined; mirror the
    platform-validated attica5/expat pattern (keep SONAME emission, skip
    versioned symlinks) to satisfy the CI L5 gate.
  - Qt mkspecs compat: the native Qt5CoreConfigExtrasMkspecDir.cmake probes
    <qt_pkg>/../b/mkspecs/linux-clang (baked build dir, absent in the
    published package); mirror the tree (attica-kf5/5.116.0 precedent) and
    expose it via -isystem for <qplatformdefs.h> users.
  - Qt5::qmake target injection: upstream KDQtInstallPaths.cmake (included
    unconditionally at CMakeLists.txt:302 for the Qt frontend) hard-requires
    a Qt5::qmake/qtpaths target and runs "qmake -query". The CMakeDeps
    Qt5Config has no qmake component, so an imported Qt5::qmake target
    pointing at the package's bin/qmake is injected via CMAKE_PROJECT_INCLUDE.
  - Qt5Test config shim: developer mode issues a standalone
    find_package(Qt5Test 5.15 REQUIRED) (src/CMakeLists.txt:436,
    tests/CMakeLists.txt:16); CMakeDeps only generates Qt5Config.cmake
    (which does declare a Qt5::Test component), so generate() writes a
    Qt5TestConfig.cmake shim over the generated config plus a matching
    Qt5TestConfigVersion.cmake into the generators folder.
  - QtTest window-helper shim: the OHOS Qt5 port strips the window-helper
    API that stock Qt 5.15 declares at the end of
    qtest_gui.h/qtest_widgets.h (QTest::qWaitForWindowActive /
    qWaitForWindowExposed for QWindow and QWidget), and its QtGui include
    chain no longer completes QWindow/QGuiApplication in test TUs.
    Upstream calls QTest::qWaitForWindowActive(QWidget*) once
    (tests/qtwidgets/tst_qtwidgets.cpp:3083) and tst_native_qpa.cpp
    dereferences QWindow/qGuiApp, so a shim header restoring the missing
    surface is force-included via add_compile_options(-include) — the
    upstream sources stay patch-free.
  - Tests: build() records the upstream ctest inventory only (ctest -N,
    R51 step 1). Full execution happens on the real OHOS PC device with
    QT_QPA_PLATFORM=offscreen (qt5-qtbase ships the offscreen QPA plugin;
    xcb is unavailable on OHOS); evidence is committed under reports/
    (R51 steps 2-3).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# Force-included into every TU of the package build (see generate()). The
# OHOS Qt5 port (qt5-qtbase/5.15.2.2) ships a reduced QtTest module: the
# window-helper API stock Qt 5.15 declares at the end of
# qtest_gui.h/qtest_widgets.h (QTest::qWaitForWindowActive/qWaitForWindowExposed
# for QWindow and QWidget) was stripped, and the QtGui include chain no longer
# completes QWindow/QGuiApplication in test TUs. Upstream kddockwidgets 2.4.0
# calls QTest::qWaitForWindowActive(QWidget*) once
# (tests/qtwidgets/tst_qtwidgets.cpp:3083) and tst_native_qpa.cpp dereferences
# QWindow/qGuiApp. This header restores exactly the missing surface on top of
# the public Qt API (stock semantics: poll the window's active state until the
# timeout elapses), keeping the upstream sources patch-free. QTest::qWait is
# not used here because this header is force-included before <QtTest/QTest>.
#
# Verified on the real OHOS PC device: the offscreen QPA simulates window
# activation (probe: QWindow::requestActivate/QWidget::activateWindow +
# isActive/isActiveWindow both report active), so the stock polling loop
# terminates successfully.
KDDW_QT_WINDOWACTIVE_SHIM = r"""#pragma once
#include <QWindow>
#include <QGuiApplication>
#include <QWidget>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QCoreApplication>

namespace QTest {

// Stock Qt 5.15 qtest_widgets.h: wait until the widget's window is active,
// or the timeout elapses. Mirrors the stock implementation's polling loop
// (QTest::qWait replaced by the blocking processEvents wait, since this
// header is force-included before <QtTest/QTest> is visible).
inline bool qWaitForWindowActive(QWidget *widget, int timeout = 5000)
{
    if (!widget)
        return false;
    QWindow *window = widget->windowHandle();
    if (!window) {
        widget->show();
        window = widget->windowHandle();
    }
    if (!window)
        return false;
    window->requestActivate();
    QElapsedTimer timer;
    timer.start();
    while (!window->isActive()) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
        if (timer.elapsed() >= timeout)
            break;
    }
    return window->isActive();
}

} // namespace QTest
"""


class KddockwidgetsConan(ConanFile):
    name = "kddockwidgets"
    version = "2.4.0"
    description = "KDAB's Qt docking framework (QtWidgets docking system)"
    license = "GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://github.com/KDAB/KDDockWidgets"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5::Widgets is the PUBLIC link dependency of the kddockwidgets
        # target; Qt5::Test is needed by the upstream autotest suite
        # (KDDockWidgets_TESTS=ON). qt5-qtbase/5.15.2.2 is the OHOS Qt5
        # build that ships both modules.
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Regenerate a clean Qt5Config so find_package(Qt5 COMPONENTS ...)
        # works (kglobalaccel/attica5 precedent).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["KDDockWidgets_QT6"] = "OFF"
        tc.variables["KDDockWidgets_FRONTENDS"] = "qtwidgets"
        tc.variables["KDDockWidgets_EXAMPLES"] = "OFF"
        # Upstream gates add_subdirectory(tests) on KDDockWidgets_TESTS AND
        # KDDockWidgets_DEVELOPER_MODE (CMakeLists.txt:620: "Always build the
        # test harness in developer-mode"), so both must be enabled. Developer
        # mode only adds -Wall/-Wextra + QT_FORCE_ASSERTS (PRIVATE) and two
        # harmless PUBLIC defines on the library target; the gcc>14-only
        # -fhardened branch and the spdlog REQUIRE branch are skipped in this
        # configuration (clang 15, NO_SPDLOG=ON).
        tc.variables["KDDockWidgets_TESTS"] = "ON"
        tc.variables["KDDockWidgets_DEVELOPER_MODE"] = "ON"
        tc.variables["KDDockWidgets_NO_SPDLOG"] = "ON"
        tc.variables["KDDockWidgets_X11EXTRAS"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        for tool, var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
            ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
        ):
            tool_path = os.path.join(qt5.package_folder, "bin", tool)
            if not os.path.isfile(tool_path):
                raise RuntimeError(
                    "qt5-qtbase/5.15.2.2 does not provide the required bin/%s tool"
                    % tool
                )
            tc.variables[var] = tool_path

        qmake = os.path.join(qt5.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/qmake tool"
            )

        # Upstream CMakeLists includes cmake/KDAB/modules/KDQtInstallPaths.cmake,
        # which hard-requires a Qt5::qmake (or Qt5::qtpaths) target and then runs
        # "qmake -query". qt5-qtbase/5.15.2.2 ships bin/qmake, but the
        # CMakeDeps-regenerated Qt5Config declares no qmake component, so the
        # target is absent and configure dies with "No supported Qt version
        # found". Inject an imported Qt5::qmake target through
        # CMAKE_PROJECT_INCLUDE (processed right after project(), before the
        # KDQtInstallPaths include at CMakeLists.txt:302). The qmake binary is
        # an OHOS build and runs natively on the device; its -query output only
        # feeds the .pri file generation (ECM_MKSPECS_INSTALL_DIR falls back to
        # the relative mkspecs/modules when no host paths resolve).
        qmake_target_file = os.path.join(
            self.generators_folder, "kddockwidgets_qmake_target.cmake"
        )
        with open(qmake_target_file, "w") as f:
            f.write(
                "# Injected by the kddockwidgets recipe: upstream\n"
                "# KDQtInstallPaths.cmake requires a Qt5::qmake/qtpaths target.\n"
                'if(NOT TARGET Qt5::qmake)\n'
                "  add_executable(Qt5::qmake IMPORTED)\n"
                "  set_target_properties(Qt5::qmake PROPERTIES\n"
                '    IMPORTED_LOCATION "%s")\n'
                "endif()\n" % qmake
            )
        # The qtwidgets frontend links Qt5::WidgetsPrivate PRIVATE
        # (src/CMakeLists.txt:381). In our configuration the only private Qt
        # headers actually included are QtGui/private/qhighdpiscaling_p.h
        # (core/WidgetResizeHandler.cpp:40, qtcommon/Window.cpp:22) plus its
        # QtCore/private/qglobal_p.h dependency; the other private includes in
        # the tree belong to the unbuilt qtquick frontend or the Qt6-only
        # qtx11extras_p.h branch. qt5-qtbase/5.15.2.2 ships those private
        # headers (include/<Module>/<ver>/<Module>/private) but provides no
        # WidgetsPrivate component, so map the private module to the public
        # Qt5::Widgets library (same .so) and expose the private header roots.
        private_roots = []
        found_modules = set()
        for module in ("QtGui", "QtCore", "QtWidgets"):
            module_dir = os.path.join(qt5.package_folder, "include", module)
            if os.path.isdir(module_dir):
                for entry in os.listdir(module_dir):
                    private_dir = os.path.join(
                        module_dir, entry, module, "private"
                    )
                    if os.path.isdir(private_dir):
                        private_roots.append(
                            os.path.join(module_dir, entry).replace("\\", "/")
                        )
                        found_modules.add(module)
        if not {"QtGui", "QtCore"}.issubset(found_modules):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not ship the QtGui/QtCore private "
                "headers required by kddockwidgets"
            )
        with open(qmake_target_file, "a") as f:
            f.write(
                "\n# Injected by the kddockwidgets recipe: upstream links\n"
                "# Qt5::WidgetsPrivate PRIVATE (src/CMakeLists.txt:381) and\n"
                "# the qt5-qtbase package provides no such component. Map it\n"
                "# to the public Qt5::Widgets and expose the Qt private\n"
                "# header roots needed by the qtwidgets frontend.\n"
                "if(NOT TARGET Qt5::WidgetsPrivate)\n"
                "  add_library(Qt5::WidgetsPrivate INTERFACE IMPORTED)\n"
                "  target_link_libraries(Qt5::WidgetsPrivate INTERFACE Qt5::Widgets)\n"
                "  target_include_directories(Qt5::WidgetsPrivate INTERFACE\n"
            )
            for root in private_roots:
                f.write('    "%s"\n' % root)
            f.write("  )\nendif()\n")
        tc.variables["CMAKE_PROJECT_INCLUDE"] = qmake_target_file

        # The OHOS Qt5 port strips the QtTest window-helper API (see the
        # KDDW_QT_WINDOWACTIVE_SHIM comment above). Force-include the shim
        # into every TU so the upstream tests compile and behave exactly as
        # on stock Qt 5.15 — no upstream source changes.
        shim_header = os.path.join(
            self.generators_folder, "kddw_qt_windowactive_shim.h"
        ).replace("\\", "/")
        with open(shim_header, "w") as f:
            f.write(KDDW_QT_WINDOWACTIVE_SHIM)
        with open(qmake_target_file, "a") as f:
            f.write(
                "\n# Force-include the QtTest window-helper shim (OHOS Qt5\n"
                "# port strips qWaitForWindowActive from testlib; see the\n"
                "# kddw_qt_windowactive_shim.h header written by generate()).\n"
                'add_compile_options(-include "%s")\n' % shim_header
            )

        # Upstream developer mode issues a standalone
        # find_package(Qt5Test 5.15 REQUIRED) (src/CMakeLists.txt:436,
        # tests/CMakeLists.txt:16), which looks for a Qt5TestConfig.cmake —
        # CMakeDeps only generates Qt5Config.cmake, so the standalone lookup
        # dies with "Could not find a package configuration file provided by
        # 'Qt5Test'" (round 7, G2). The generated Qt5Config does declare a
        # Qt5::Test component, so shim the standalone package config over it
        # (the generators folder is on CMAKE_PREFIX_PATH via the toolchain)
        # and provide the matching version file for the 5.15 version check.
        with open(
            os.path.join(self.generators_folder, "Qt5TestConfig.cmake"), "w"
        ) as f:
            f.write(
                "# Injected by the kddockwidgets recipe: upstream developer\n"
                "# mode issues a standalone find_package(Qt5Test 5.15\n"
                "# REQUIRED) (src/CMakeLists.txt:436) while CMakeDeps only\n"
                "# generates Qt5Config.cmake. The generated config already\n"
                "# declares the Qt5::Test component, so shim the standalone\n"
                "# package over it.\n"
                'if(NOT DEFINED Qt5Test_VERSION)\n'
                '  set(Qt5Test_VERSION "5.15.2")\n'
                "endif()\n"
                'if(NOT TARGET Qt5::Test)\n'
                '  include("${CMAKE_CURRENT_LIST_DIR}/Qt5Config.cmake")\n'
                "endif()\n"
            )
        with open(
            os.path.join(self.generators_folder, "Qt5TestConfigVersion.cmake"),
            "w",
        ) as f:
            f.write(
                '# Injected by the kddockwidgets recipe (Qt5Test shim).\n'
                'set(PACKAGE_VERSION "5.15.2")\n'
                "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)\n"
                "  set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
                "else()\n"
                "  set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
                "  if(PACKAGE_VERSION STREQUAL PACKAGE_FIND_VERSION)\n"
                "    set(PACKAGE_VERSION_EXACT TRUE)\n"
                "  endif()\n"
                "endif()\n"
            )

        # The upstream autotests include <qplatformdefs.h>, which lives in the
        # Qt mkspecs tree; CMakeDeps-generated Qt5::Core configs carry only
        # the include/ directories. Expose the package mkspecs dir through the
        # build env (kglobalaccel/5.116.0 precedent).
        mkspecs_dir = os.path.join(qt5.package_folder, "mkspecs", "linux-clang")
        if os.path.isdir(mkspecs_dir):
            self.buildenv.append("CXXFLAGS", "-isystem {}".format(mkspecs_dir))

        tc.generate()

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Qt5CoreConfigExtrasMkspecDir.cmake hardcodes the qtbase *build*
        # directory (<pkg>/../b/mkspecs/linux-clang) which is not shipped in
        # the published package; mirror it so consumer find_package() works
        # (attica-kf5/5.116.0 precedent).
        source = os.path.join(qt_package_folder, "mkspecs", "linux-clang")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs", "linux-clang"
        )
        if os.path.isdir(source) and not os.path.exists(expected):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._runtime_env().vars(self).apply():
            cmake.build()
        self._record_test_inventory()

    def _runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        # The built shared library lands in <build>/lib, not <build>/bin
        # (verified on the real device). The OHOS musl loader ignores ELF
        # RUNPATH and resolves only through LD_LIBRARY_PATH, so the build
        # tree lib dir must be covered explicitly (see notes.md R51 step 2
        # execution pitfall).
        runtime_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib")
        )
        runtime_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, "bin")
        )
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        return runtime_env

    def _record_test_inventory(self):
        # R51 step 1: record the upstream ctest inventory only. Full execution
        # is performed on the real OHOS PC device (offscreen QPA), with the
        # evidence committed under reports/ (see notes.md 真机验证 section).
        test_env = self._runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with test_env.vars(self).apply():
            self.run('ctest --test-dir "{}" -N'.format(self.build_folder))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "KDDockWidgets")
        self.cpp_info.set_property("cmake_target_name", "KDAB::kddockwidgets")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["kddockwidgets"]
