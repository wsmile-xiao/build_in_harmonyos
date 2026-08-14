#!/usr/bin/env python3
"""Conan test_package for graphite2 1.3.14.

R34: This test substantively depends on the graphite2 package by
calling gr_engine_version() to verify the library is correctly
linked and functional.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class Graphite2TestConan(ConanFile):
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
        # Use bash to wrap binary execution (same pattern as icu4c test_package).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not bash:
            raise RuntimeError("bash is required to run test binaries on OHOS")
        self.run(f"{bash} -c './test_graphite2'", env="conanrun")
