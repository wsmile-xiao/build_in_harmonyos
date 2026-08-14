#!/usr/bin/env python3
"""Conan test_package for icu4c 78 — Conan L1 official test.

Uses CMake to build the test (CMakeLists.txt already exists).
CMakeToolchain handles compiler settings automatically (R33 compliant).
CI runs this automatically via `conan create` (which invokes test_package).

R34: test calls real ICU APIs (u_init, u_getUnicodeVersion, u_errorName, u_isalpha).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class Icu4cTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host: skip test")
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        # R33: find bash dynamically, avoid hardcoding paths
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not bash:
            raise RuntimeError("bash is required to run test binaries on OHOS (mksh cannot execute ELF). Set CONFIG_SHELL or install bash.")
        self.run(f"{bash} -c './test_icu4c'", env="conanrun")
