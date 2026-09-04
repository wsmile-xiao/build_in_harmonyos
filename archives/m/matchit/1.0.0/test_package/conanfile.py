#!/usr/bin/env python3
"""test_package conanfile — matchit 1.0.0 consumer smoke test."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run
import os


class MatchitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain is instantiated manually in generate() (for the OHOS
    # platform mapping), so only CMakeDeps is declared here.
    generators = "CMakeDeps"

    def requirements(self):
        # Test the package under creation (conan create passes the reference
        # via self.tested_reference_str).
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeToolchain is auto-generated from the generators attribute; only
        # inject the OHOS platform mapping here.
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindir, "test_matchit"),
                     env="conanrun")
