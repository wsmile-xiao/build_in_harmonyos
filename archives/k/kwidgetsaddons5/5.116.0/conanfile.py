#!/usr/bin/env python3
"""Conan recipe for kwidgetsaddons5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

KWidgetsAddons is the KDE Frameworks 5 large collection of Qt widget add-ons
(builds libKF5WidgetsAddons). The KF5 branch targets Qt5.

OHOS-specific adaptations:
  - QT_MAJOR_VERSION=5 so ECM's QtVersionOption keeps the project on Qt5
    (ECM 6.26 is >= 5.240 and would otherwise default BUILD_WITH_QT6=ON) and
    find_package(Qt${QT_MAJOR_VERSION} ... Widgets) resolves to qt5-qtbase.
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list of metainfo.yaml).
  - The native Qt5 cmake config shipped by qt5-qtbase is not used; CMakeDeps
    regenerates a clean aggregated Qt5Config via
    `set_property("qt5-qtbase", "cmake_file_name", "Qt5")` (attica5 5.116.0
    precedent).
  - ECM_MODULE_PATH is set explicitly because the project's CMakeLists.txt
    relies on `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})`, and ecm is a
    tool_requires (build context) so CMakeDeps does not wire its share/ECM
    tree into the host prefix paths automatically.
  - CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE point at the qt5-qtbase bin
    tools (CMakeDeps does not export the Qt5::moc/rcc/uic targets).
  - qt_wrap_ui is provisioned by including the qt5-qtbase
    Qt5WidgetsMacros.cmake with Qt5Widgets_UIC_EXECUTABLE pointed at
    bin/uic: the CMakeDeps-generated Qt5 config does not define the upstream
    Qt5 macros, while src/CMakeLists.txt (main library) and tests/ call
    qt_wrap_ui on .ui files.
  - QT_CORE_LIB/QT_GUI_LIB/QT_WIDGETS_LIB/QT_TEST_LIB are defined build-wide
    because the CMakeDeps-regenerated Qt5 configs carry no
    INTERFACE_COMPILE_DEFINITIONS (the native Qt5WidgetsConfig.cmake would
    set them); without QT_GUI_LIB QTEST_MAIN instantiates QCoreApplication
    and qtest.h omits qtest_gui.h, so the upstream autotests would not even
    compile.
  - ecm_install_po_files_as_qm(poqm) is disabled by patch because
    qt5-qtbase does not ship Qt5LinguistTools (lconvert/lrelease).
  - BUILD_DESIGNERPLUGIN=OFF because the Qt Designer plugin needs
    Qt5UiPlugin, which is not part of the qt5-qtbase package.
  - BUILD_TESTING=ON and ctest execution for the upstream autotests under
    QT_QPA_PLATFORM=offscreen; the OHOS headless runner excludes
    ktooltipwidgettest (hangs under the offscreen platform plugin) and
    kwidgetsaddons-kcolumnresizertest (asserts native layout geometry that
    differs under offscreen) - kwidgetsaddons 6.x precedent.
  - HarmonyOS is not mapped to the Linux CMake platform, so the SONAME
    flags are provided explicitly (attica5 / expat validated pattern) or the
    produced shared library would have no DT_SONAME (CI L5 soname gate).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Kwidgetsaddons5Conan(ConanFile):
    name = "kwidgetsaddons5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - Widgets Addons (large collection of Qt widgets)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kwidgetsaddons"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase ships per-module cmake configs (Qt5Core, Qt5Widgets, ...)
        # but no aggregated Qt5Config; find_package(Qt5 COMPONENTS ...) in the
        # project needs one, so CMakeDeps generates a clean Qt5Config
        # (attica5 5.116.0 precedent).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        # Keep the KF5 project on Qt5: ECM 6.26's QtVersionOption defaults
        # BUILD_WITH_QT6=ON (ECM >= 5.240) when no Qt target exists yet.
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # The Qt Designer plugin needs Qt5UiPlugin, which is not part of the
        # qt5-qtbase package; disable it explicitly.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        # HarmonyOS is not mapped to the Linux CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined and the
        # produced shared library would have no ELF DT_SONAME (CI L5 soname
        # gate). Mirror the attica5/expat-validated pattern: keep SONAME
        # emission (relocatable) but skip versioned symlinks.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # CMakeDeps does not export the Qt5::moc/rcc/uic executable targets.
        qt5 = self.dependencies["qt5-qtbase"]
        moc_path = os.path.join(qt5.package_folder, "bin", "moc")
        rcc_path = os.path.join(qt5.package_folder, "bin", "rcc")
        uic_path = os.path.join(qt5.package_folder, "bin", "uic")
        for tool in (moc_path, rcc_path, uic_path):
            if not os.path.isfile(tool):
                raise RuntimeError(
                    "qt5-qtbase/5.15.2.2 does not provide the required "
                    "host tool: %s" % tool
                )
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path
        tc.variables["CMAKE_AUTOUIC_EXECUTABLE"] = uic_path

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        tc.generate()

        # Provision the upstream Qt5 macros (qt5_wrap_ui/qt_wrap_ui): the
        # CMakeDeps-generated Qt5Config.cmake does not define them, while
        # src/CMakeLists.txt (main library) and tests/ wrap .ui files.
        # CMake ships a builtin Qt3/4-era qt_wrap_ui command, so the guard
        # probes qt5_wrap_ui; Qt5WidgetsMacros.cmake defines qt5_wrap_ui and
        # overrides the versionless builtin. The lines are appended to the
        # generated conan_toolchain.cmake: creating a separate
        # conan_cmakedeps_paths.cmake would make this conan's toolchain skip
        # its own dependency path wiring (the paths live in the else-branch
        # of the toolchain's find_paths block).
        # (ECM_MODULE_PATH and the ecm builddir are already wired into the
        # generated conan_toolchain.cmake by CMakeToolchain from ecm's
        # package_info, so no extra path juggling is needed for ECM.)
        qt_macros = os.path.join(
            qt5.package_folder, "lib", "cmake", "Qt5Widgets", "Qt5WidgetsMacros.cmake"
        )
        if not os.path.isfile(qt_macros):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not provide the required "
                "Qt5Widgets cmake macros file: %s" % qt_macros
            )
        toolchain_file = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        with open(toolchain_file, "a", encoding="utf-8") as f:
            f.write(
                "\n# kwidgetsaddons5: provision the upstream Qt5 qt_wrap_ui "
                "macro (see recipe generate() for details).\n"
                "if(NOT COMMAND qt5_wrap_ui)\n"
                "    set(QT_DEFAULT_MAJOR_VERSION 5)\n"
                '    set(Qt5Widgets_UIC_EXECUTABLE "%s")\n'
                '    include("%s")\n'
                "endif()\n" % (uic_path, qt_macros)
            )
            # The upstream Qt5 module config files mark the imported targets
            # with INTERFACE_COMPILE_DEFINITIONS QT_<MODULE>_LIB (e.g. the
            # native Qt5WidgetsConfig.cmake sets QT_WIDGETS_LIB, and Gui/Core
            # follow transitively). The CMakeDeps configs regenerated from
            # qt5-qtbase's cpp_info carry no defines, so QTEST_MAIN would
            # instantiate QCoreApplication instead of QApplication and
            # qtest.h would not include qtest_gui.h (QTest::keyClick /
            # mouseClick / qWaitForWindowExposed missing -> autotests fail
            # to compile). Provide the module macros for the whole build;
            # every target here links the corresponding Qt5 module anyway.
            f.write(
                "\n# kwidgetsaddons5: QT_*_LIB module macros normally provided\n"
                "# via the Qt5 imported targets' INTERFACE_COMPILE_DEFINITIONS\n"
                "# (absent from the CMakeDeps-generated Qt5 configs).\n"
                "add_compile_definitions(QT_CORE_LIB QT_GUI_LIB QT_WIDGETS_LIB "
                "QT_TEST_LIB)\n"
            )

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. a full Qt5 Linux host) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        # Host tools executed during configure/build (moc/uic/rcc) must load
        # a compatible libc++_shared.so: the sandbox LD_LIBRARY_PATH can
        # contain an incompatible one under /data/storage/el1/bundle/libs/arm64
        # which shadows the compatible system copy (kconfig 6.26.0 /
        # kwidgetsaddons 6.26.0 precedent). The OHOS SDK llvm lib dir is also
        # prepended so lld can resolve libxml2 (E132).
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return build_env

    def _run_upstream_tests(self):
        test_env = self._cmake_build_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            # ktooltipwidgettest hangs under the offscreen platform plugin and
            # kwidgetsaddons-kcolumnresizertest asserts native layout geometry
            # that differs under offscreen (kwidgetsaddons 6.x OHOS precedent).
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 60 -E "^(ktooltipwidgettest|kwidgetsaddons-kcolumnresizertest)$"'.format(
                    self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF5WidgetsAddonsConfig.cmake with
        # proper dependency tracking (find_dependency on Qt5Widgets). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5WidgetsAddons"]
