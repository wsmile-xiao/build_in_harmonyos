#!/usr/bin/env python3
"""Conan test_package — vvenc 1.14.0 (consumer use case, L1 test).

Verifies that the packaged library can be consumed through Conan
(family `find_package(vvenc)` + target `vvenc::vvenc`), that the shared library
is reachable as a plain regular file on OHOS, and that the public encoder API
can be driven end to end by a downstream consumer.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class VvencTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092 applies to the consumer as well: this worker's ``uname`` reports
        # HarmonyOS and CMake ships no ``Platform/HarmonyOS`` module, so without
        # an explicit system name the consumer is configured as an unknown
        # platform ("System is unknown to cmake") and loses the Linux
        # runtime-path handling.  The test binary would then only find
        # ``libvvenc.so`` through the ``conanrun`` LD_LIBRARY_PATH.  Pinning the
        # system name keeps it runpath-correct.
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_vvenc"), env="conanrun")
