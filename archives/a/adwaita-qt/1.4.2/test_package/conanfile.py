#!/usr/bin/env python3
"""Consumer test for adwaita-qt without a display server."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class AdwaitaQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()
        package = self.dependencies["adwaita-qt"]
        qtbase = self.dependencies["qtbase"]
        package_prefix = package.package_folder.replace("\\", "/")
        qt_prefix = qtbase.package_folder.replace("\\", "/")

        tc = CMakeToolchain(self)
        tc.cache_variables["AdwaitaQt6_DIR"] = (
            f"{package_prefix}/lib/cmake/AdwaitaQt6"
        )
        tc.cache_variables["CMAKE_PREFIX_PATH"] = (
            f"{package_prefix}/lib/cmake;{qt_prefix}/lib/cmake"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "adwaita-qt test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_adwaita_qt")
            package = self.dependencies["adwaita-qt"]
            plugin_root = os.path.join(package.package_folder, "lib", "qt6", "plugins")
            os.environ["QT_PLUGIN_PATH"] = plugin_root
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            self.run(executable, env="conanrun", ignore_errors=False)
