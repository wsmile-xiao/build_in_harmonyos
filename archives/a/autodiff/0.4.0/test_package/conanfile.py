#!/usr/bin/env python3
"""Conan test_package — autodiff 0.4.0

Consumer test: find_package(autodiff) + autodiff::autodiff + verify
forward-mode (dual) and reverse-mode (var) automatic differentiation APIs.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class AutodiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            cmake_arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = cmake_arch
            tc.extra_exelinkflags.append("-static")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS test package"
                )
            for name in ("autodiff_forward_test", "autodiff_reverse_test"):
                self.run(
                    f'"{qemu}" "{os.path.join(bindir, name)}"',
                    env="conanrun",
                )
        else:
            for name in ("autodiff_forward_test", "autodiff_reverse_test"):
                self.run(os.path.join(bindir, name), env="conanrun")
