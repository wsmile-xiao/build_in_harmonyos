#!/usr/bin/env python3
"""Conan test_package — c-vtapi 0.0-git20230329.226eda8.

Consumer verification: builds a small C program that exercises the real
library API (VtApiPage_new / setApiKey / get / put) and links it against
the packaged library via CMakeDeps.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CvtapiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The published jansson/2.15.1.1 recipe declares cpp_info.libs only,
        # so its CMakeDeps target carries no INTERFACE_INCLUDE_DIRECTORIES
        # (jansson_INCLUDE_DIRS_RELEASE is empty), yet the package ships the
        # headers under package_folder/include.  c-vtapi's installed public
        # headers (VtObject.h -> jansson.h) genuinely need them, so inject
        # the include dir explicitly for this consumer compile.
        tc = CMakeToolchain(self)
        jansson = self.dependencies["jansson"]
        tc.variables["JANSSON_INCLUDE_DIR"] = os.path.join(
            jansson.package_folder, "include")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d: test() must contain a real self.run() execution — run the
        # HarmonyOS-specific test binary directly (real API calls, offline).
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_ohos"),
            env="conanrun",
        )
