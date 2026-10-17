#!/usr/bin/env python3
"""Consumer test for lightmapper 2.8 (header-only).

Exercises the library's CPU-side image post-processing API
(lmImageMin/lmImageMax/lmImageClamp/lmImageDilate/lmImageFtoUB/
lmImageSaveTGAub) with real buffers and assertions.  The GL symbols the
single header references are satisfied at link time by gl_shim.c stubs;
they are never executed because the test only calls CPU-side APIs.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LightmapperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_C_STANDARD"] = "99"
        tc.cache_variables["CMAKE_C_STANDARD_REQUIRED"] = True
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_lightmapper")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the lightmapper consumer test"
                )
            self.run(f'"{qemu}" "{executable}"', env="conanrun")
        else:
            self.run(executable, env="conanrun")