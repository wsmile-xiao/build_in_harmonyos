#!/usr/bin/env python3
"""Conan test_package for kholidays5 5.116.0 (L1 official test).

Consumer-side verification (R34): the C++ test links KF5::Holidays and
drives the real public API the way downstream KDE consumers (Plasma
calendar / eventviews / holiday plugins) use it — HolidayRegion
rawHolidaysWithAstroSeasons round-trip, isHoliday for a known date,
SunRiseSet utcSunrise/utcSunset, LunarPhase phaseAtDate, Zodiac
signAtDate/signName — plus HarmonyOS-specific checks (R53): the loaded
libKF5Holidays.so carries the unversioned DT_SONAME and a DT_RUNPATH
(E537 install-RPATH adaptation), parsed straight from the ELF dynamic
section of the consumer-visible package path.

test() really executes the built binary through self.run() (L0d / R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KHolidays5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Same Linux-like platform force as the library build (chain-
            # wide convention, kpeople5/kcalcore precedent): the native
            # Qt5 configs apply their POSIX settings and the consumer
            # build behaves exactly like the library build it verifies.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if str(self.settings.arch) == "armv8":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            elif str(self.settings.arch) == "x86_64":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "x86_64"
        tc.generate()

        pkg = self.dependencies.get("kholidays5")
        qtbase = self.dependencies.get("qt5-qtbase")
        # Same native-config wiring as the library build: the recipe's
        # package_info exposes the project-installed KF5HolidaysConfig.cmake
        # (cmake_find_mode=none) and qt5-qtbase ships its native Qt5
        # configs, so both package roots are wired onto the CMake search
        # paths through conan_cmakedeps_paths.cmake (kcoreaddons5 /
        # kcalcore test_package precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg and pkg.package_folder:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                % pkg.package_folder
            )
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % qt_pkg)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _build_env(self):
        # The Qt host tools executed during configure (if any) need the
        # compatible libc++ loaded first (kpeople5 test_package precedent).
        env = Environment()
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "UTC")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kholidays5"),
                env="conanrun",
            )
