#!/usr/bin/env python3
"""Conan test_package for bstring 1.0.3 — Conan L1 official test.

Uses CMake (CMakeDeps + CMakeToolchain) so the compiler is handled
by Conan toolchain, not raw shell env vars (R33).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class BstringTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()
        # Generate LD_LIBRARY_PATH for shared library runtime
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries.
        # Use bash to wrap binary execution (R5: OHOS has no /bin/sh).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Set LD_LIBRARY_PATH for shared library runtime
        lib_dir = os.path.join(self.dependencies["bstring"].package_folder, "lib")
        self.run(f"LD_LIBRARY_PATH={lib_dir} {bash} -c './test_bstring'")
