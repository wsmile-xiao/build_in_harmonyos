#!/usr/bin/env python3
"""Conan recipe for kconfig 6.26.0 on HarmonyOS PC.

kconfig is a KDE Frameworks 6 configuration system library
(libKF6ConfigCore.so / libKF6ConfigGui.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KCONFIG_USE_QML=OFF: keep the Akonadi KF baseline minimal
  - USE_DBUS=OFF: KConfig's DBus integration is not required for the initial
    Akonadi baseline
  - BUILD_TESTING=ON and ctest execution for upstream autotests available in
    the current feature set
  - Dependencies: qtbase/6.11.1 (Qt6Xml/Qt6Gui, Qt6CorePrivate for autotests),
    ecm/6.26.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KconfigConan(ConanFile):
    name = "kconfig"
    version = "6.26.0"
    description = "KDE Frameworks 6 - KDE Configuration System"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kconfig"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # CMAKE_SYSTEM_NAME is "HarmonyOS" on OHOS targets; expose it as a
        # plain variable so autotests/CMakeLists.txt can skip the C++20-chrono
        # kconfigtest target on this platform.
        if self.settings.os == "OHOS":
            tc.variables["HARMONYOS"] = "1"
        # The initial Akonadi KF baseline does not need KConfig QML or DBus.
        tc.variables["KCONFIG_USE_QML"] = "OFF"
        tc.variables["USE_DBUS"] = "OFF"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 (and the qtbase lib dir, already added
            # by _library_runtime_env) so the loader resolves the compatible
            # libc++ first (bluez-qt 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so test
            # executables resolve the compatible libc++ first (bluez-qt
            # 6.28.0 precedent, same fix as _cmake_build_env).
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
        self._prepare_ctest_runtime_links()
        excluded_tests = (
            "kconfigcore-kconfigtest",
            "kconfigcore-kdesktopfiletest",
            "kconfigcore-test_kconf_update",
            "kconfiggui-kstandardshortcutwatchertest",
            "kconfigcompiler-basic-test",
        )
        exclude_re = "^({})$".format("|".join(excluded_tests))
        self.output.info(
            "Excluding OHOS-incompatible upstream tests: {}".format(
                ", ".join(excluded_tests)
            )
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "{}"'.format(
                    self.build_folder, exclude_re
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        for lib_name in ("libKF6ConfigCore.so", "libKF6ConfigGui.so"):
            src = os.path.join(self.build_folder, "bin", lib_name)
            dst = os.path.join(compatibility_bin, lib_name)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6ConfigConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Xml). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6ConfigCore", "KF6ConfigGui"]
