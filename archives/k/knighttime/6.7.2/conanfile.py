#!/usr/bin/env python3
"""Conan recipe for knighttime 6.7.2 on HarmonyOS PC.

knighttime is the KDE Plasma "Night Time" helper: the KNightTime library
(libKNightTime.so) provides the dark-light cycle schedule API
(KDarkLightSchedule, KDarkLightScheduleProvider, KDarkLightSubscription)
built on KHolidays::SunEvents, plus the knighttimed daemon that applies the
schedule (colour temperature / dark-light state) over D-Bus.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list), same as kconfig/kdbusaddons/kholidays precedents
  - BUILD_TESTING=ON and ctest execution for the 3 upstream autotests
    (transition-test, cycle-test, schedule-test)
  - The upstream daemon needs a live D-Bus session bus to do anything
    useful; it is still built and installed, but the recipe's tests focus on
    the library (the autotests link the library only)
  - Dependencies: qtbase/6.11.1.1 (Qt6::Core/DBus/Positioning, aligned with kdbusaddons),
    kholidays/6.28.0 (KHolidays::SunEvents, published by the companion
    kholidays PR), kconfig/6.26.0 + kcoreaddons/6.26.0 + kdbusaddons/6.29.0
    + ki18n/6.26.0 (daemon), extra-cmake-modules/6.29.0 (ECM >= 6.26.0
    required upstream)
  - tc.blocks.remove("cppstd") + CMAKE_CXX_STANDARD=20: upstream sets
    C++23; the OHOS toolchain (clang 15 / libc++) compiles the sources
    cleanly under C++20 and the repo profile pins cppstd=17
    (kholidays/baloo precedent)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none (kholidays/kdbusaddons precedent)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KnighttimeConan(ConanFile):
    name = "knighttime"
    version = "6.7.2"
    description = ("KDE Plasma KNightTime - dark-light cycle schedule "
                   "library and daemon (KDarkLightSchedule on "
                   "KHolidays::SunEvents)")
    license = "BSD-3-Clause AND LGPL-2.1-or-later AND GPL-2.0-or-later"
    homepage = "https://invent.kde.org/plasma/knighttime"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KNightTime library: Qt6::Core public, Qt6::DBus private.
        self.requires("qtbase/6.11.1")
        # Qt6::DBus lives only in the qtbase-sql-dbus variant (the plain
        # qtbase/6.11.1 package is built with FEATURE_dbus=OFF; the two
        # packages coexist by design, see qtbase-sql-dbus notes).
        self.requires("qtbase-sql-dbus/6.11.1")
        # Qt6::Positioning for the solar scheduler in the daemon.
        self.requires("qtpositioning/6.11.1")
        # KHolidays::SunEvents computes the sun-driven schedule (private
        # link of the library, public dependency of the daemon chain).
        self.requires("kholidays/6.28.0")
        # knighttimed daemon: KF6 Config/CoreAddons/DBusAddons + Qt6
        # Positioning/DBus. ki18n is pulled by the framework chain for the
        # translation domain macro (TRANSLATION_DOMAIN definitions).
        # kdbusaddons 6.18.0 is the qtbase-sql-dbus-ecosystem build
        # (KF6::DBusAddons for KDBusService); the 6.26.0 version gate in
        # the upstream find_package is relaxed by patch 0002.
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("ki18n/6.26.0")

    def build_requirements(self):
        # ECM >= 6.26.0 is REQUIRED upstream (find_package(ECM 6.26.0)).
        self.tool_requires("extra-cmake-modules/6.29.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream sets CMAKE_CXX_STANDARD 23; the OHOS toolchain compiles
        # the sources cleanly under C++20, and the repo profile pins
        # cppstd=17. Remove the conan cppstd block so CMAKE_CXX_STANDARD=20
        # is honored (kholidays/baloo precedent).
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules are found (kholidays precedent).
        ecm = self.dependencies.build.get("extra-cmake-modules")
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
            qt_prefixes = [qt_pkg]
            # Qt6Config.cmake (whichever qtbase variant resolves first)
            # finds each requested component relative to its own prefix plus
            # QT_ADDITIONAL_PACKAGES_PREFIX_PATH. Point it at the
            # qtpositioning package root so find_package(Qt6 COMPONENTS
            # Positioning) finds Qt6PositioningConfig.cmake there.
            qtpos = self.dependencies.get("qtpositioning")
            additional = []
            if qtpos and qtpos.package_folder:
                additional.append(qtpos.package_folder)
            if additional:
                tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                    additional
                )
                lines.append(
                    'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH '
                    f'"{";".join(additional)}" CACHE STRING '
                    '"Additional directories where find(Qt6 ...) components '
                    'are searched" FORCE)'
                )
            # KF6 packages install their own CMake config trees; add every
            # non-tool dependency package's lib/cmake to the prefix path so
            # find_package(KF6...) resolves inside the conan cache. This
            # includes qtbase-sql-dbus (the Qt6::DBus provider) and
            # qtpositioning (Qt6::Positioning provider).
            for req in ("kholidays", "kconfig", "kcoreaddons",
                        "kdbusaddons", "ki18n", "qtbase-sql-dbus",
                        "qtpositioning"):
                dep = self.dependencies.get(req)
                if dep and dep.package_folder:
                    dep_cmake = os.path.join(dep.package_folder, "lib", "cmake")
                    lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep_cmake}")')
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # ECM KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure; /system/lib64 resolves the compatible libc++ first
            # (bluez-qt 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("TZ", "UTC")
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
            # Run the upstream ctest suite: 3 autotests are registered by
            # autotests/CMakeLists.txt (transition-test, cycle-test,
            # schedule-test). They link the KNightTime library only and
            # exercise the schedule computation end to end (forecast uses
            # KHolidays::SunEvents internally).
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error --timeout 300'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KNightTimeConfig.cmake with proper
        # dependency tracking. Use cmake_find_mode=none so CMakeDeps doesn't
        # shadow it (KF6 precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KNightTime"]
