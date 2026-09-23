#!/usr/bin/env python3
"""Consumer test for qt/5.15.19 without a display server."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        package_prefix = self.dependencies["qt"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = package_prefix
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration("qt test package has no build bindir")
            executable = os.path.join(bindirs[0], "test_qt5")
            test_env = Environment()
            test_env.prepend_path(
                "LD_LIBRARY_PATH",
                os.path.join(self.dependencies["qt"].package_folder, "lib"),
            )
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
            with test_env.vars(self).apply():
                self.run(
                    executable,
                    env="conanrun",
                    ignore_errors=False,
                )
