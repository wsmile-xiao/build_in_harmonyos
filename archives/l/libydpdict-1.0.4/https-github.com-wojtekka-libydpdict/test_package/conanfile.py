#!/usr/bin/env python3
"""Build and execute libydpdict consumers, including HarmonyOS storage IO."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibydpdictTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"YDPDICT_HARMONY_TEST": self.settings.os == "OHOS"})
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross build: consumers compiled; execution requires target device")
            return
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_libydpdict"), env="conanrun")
        self.run(os.path.join(bindir, "test_ydpdict_e2e"), env="conanrun")
        if self.settings.os == "OHOS":
            self.run(os.path.join(bindir, "test_harmony_storage"), env="conanrun")
