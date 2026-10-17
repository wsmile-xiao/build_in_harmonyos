#!/usr/bin/env python3
"""Conan test_package — robin-map 1.3.0

Homebrew-equivalent consumer test:
  find_package(tsl-robin-map) + tsl::robin_map + insert/print map entries.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RobinMapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["ROBIN_MAP_OHOS_TEST"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "robinmap_test")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS test package"
                )
            self.run(f"\"{qemu}\" \"{bin_path}\"", env="conanrun")
        else:
            self.run(bin_path, env="conanrun")
