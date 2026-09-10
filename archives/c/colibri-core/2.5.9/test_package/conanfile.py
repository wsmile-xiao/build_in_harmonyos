#!/usr/bin/env python3
"""Consumer test for the Colibri Core C++ API and installed commands."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ColibriCoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # HarmonyOS' CMake toolchain roots package searches in the SDK.  Point
        # CONFIG-mode lookup at the Conan generators explicitly so native and
        # cross profiles consume the exact same packaged targets.
        generators = str(self.generators_folder)
        cmake.configure(
            variables={
                "colibri-core_DIR": generators,
                "bzip2_DIR": generators,
            }
        )
        cmake.build()

    def test(self):
        executable = os.path.join(
            self.cpp.build.bindirs[0],
            "test_colibri_core.exe"
            if str(self.settings.os) == "Windows"
            else "test_colibri_core",
        )
        self.run(f'"{executable}"', env="conanrun")
        self.run("colibri-classencode -h", env="conanrun")
        self.run("colibri-ngrams -h", env="conanrun")
