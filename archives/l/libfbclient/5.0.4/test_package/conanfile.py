#!/usr/bin/env python3
"""Conan test_package for libfbclient/5.0.4 (Conan L1 test).

Consumer-side verification: links the packaged client library, loads it, and
runs real API calls (Y-Valve master interface, legacy C API version, ICU time
zone codec, remote provider attach error path) plus HarmonyOS specific checks
(toolchain, packaged ELF architecture, ICU on OHOS). See test_libfbclient.cpp.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfbclientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the checks explicitly (the binary really exercises the packaged
        # library API: master interface, version entry points, ICU time zone
        # codec, remote provider error path + HarmonyOS specific checks).
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libfbclient")
        self.run(binary, env="conanrun")
