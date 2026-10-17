#!/usr/bin/env python3
"""Consumer test for the KCompletion 5.116.0 Conan package."""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Kcompletion5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self, generator="Ninja")
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for name in (
            self.tested_reference_str.split("/")[0],
            "kconfig5",
            "kwidgetsaddons5",
        ):
            package = self.dependencies.get(name)
            if package:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s")'
                    % os.path.join(package.package_folder, "lib", "cmake")
                )
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5:
            qt_folder = qt5.package_folder
            lines.extend(
                [
                    'list(PREPEND CMAKE_PREFIX_PATH "%s")'
                    % os.path.join(qt_folder, "lib", "cmake"),
                    'list(PREPEND CMAKE_LIBRARY_PATH "%s")'
                    % os.path.join(qt_folder, "lib"),
                    'list(PREPEND CMAKE_INCLUDE_PATH "%s")'
                    % os.path.join(qt_folder, "include"),
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as paths:
            paths.write("\n".join(lines) + "\n")

    def build(self):
        env = Environment()
        for llvm_lib in sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
        ):
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib")
                )
        env.define("QT_QPA_PLATFORM", "offscreen")
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(qt5.package_folder, "plugins", "platforms"),
            )
            env.define("QT_PLUGIN_PATH", os.path.join(qt5.package_folder, "plugins"))
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        env.define("HOME", test_home)
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kcompletion5"),
                env="conanrun",
            )
