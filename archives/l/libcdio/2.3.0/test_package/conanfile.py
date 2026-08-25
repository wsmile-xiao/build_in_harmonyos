#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/l/libcdio/2.3.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibcdioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # WSL can cross-link OHOS binaries but does not have the target's
        # dynamic loader.  A static test executable remains a real API test
        # and can be executed by qemu-aarch64 without an OHOS rootfs.
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-static"
            if cross_building(self):
                tc.variables["CMAKE_CROSSCOMPILING_EMULATOR"] = "qemu-aarch64-static"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libcdio')}", env="conanrun")
