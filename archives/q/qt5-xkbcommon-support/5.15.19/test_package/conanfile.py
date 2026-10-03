#!/usr/bin/env python3
"""test_package for qt5-xkbcommon-support/5.15.19 (HarmonyOS PC).

Builds and runs a real consumer that finds the Qt5XkbCommonSupport module,
links Qt5::XkbCommonSupportPrivate and exercises QXkbCommon API from both
object files of the static module library (see src/test_xkbsupport.cpp).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Qt5XkbCommonSupportTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.generate()

        # qt5-xkbcommon-support and qt/5.15.19.1 both set cmake_find_mode=none
        # (they ship native Qt5*Config.cmake files), so CMakeDeps does not
        # advertise their package dirs: point CMake at them explicitly.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            folder = os.fspath(dep.package_folder).replace("\\", "/")
            for sub in ("lib/cmake", "lib", "include"):
                candidate = os.path.join(folder, sub)
                if not os.path.isdir(candidate):
                    continue
                if sub == "lib/cmake":
                    lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{candidate}")')
                elif sub == "lib":
                    lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{candidate}")')
                else:
                    lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{candidate}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # The module archive pulls <xkbcommon/xkbcommon.h> and libxkbcommon.so,
        # and the Qt5 shared libraries it was compiled against must load too.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        # Qt needs a platform plugin; offscreen is what the OHOS Qt5 package
        # ships (libqminimal.so / libqoffscreen.so).
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{0}" --output-on-failure'.format(self.build_folder)
            )
