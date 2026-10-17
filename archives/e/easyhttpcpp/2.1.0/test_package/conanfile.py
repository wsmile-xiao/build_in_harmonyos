#!/usr/bin/env python3
"""Conan test_package for easyhttpcpp — tests that the library API works correctly (R34).

The test builds an EasyHttp client, Request and Headers and verifies observable
values instead of only printing a string. Poco is a transitive requirement of the
public headers, so it is linked explicitly for the consumer build.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class EasyhttpcppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require Poco for include directories in test build
        self.requires("poco/1.15.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if "poco" in self.dependencies:
            incdirs = self.dependencies["poco"].cpp_info.includedirs
            if incdirs:
                tc.variables["POCO_INCLUDE_DIRS"] = ";".join(incdirs)
        tc.generate()

        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_easyhttpcpp")
        if not os.path.exists(exe):
            exe = os.path.join(self.build_folder, "test_easyhttpcpp")
        self.run(exe, env="conanrun")