#!/usr/bin/env python3
"""Conan test_package — silo-llnl 4.12.1 (Conan L1 official test).

Consumer-perspective validation of the installed libsilo + headers:
the test builds test.c (a real Silo API write/read-back round-trip on
the PDB driver — HDF5 is disabled in this build) and runs it. The test
binary itself prints the HMBS_TEST_PACKAGE_RESULT JSON marker; it flows
through self.run() into the preflight log for hmbs to capture.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SiloLlnlTestConan(ConanFile):
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
        # OHOS: /system/bin/sh cannot exec ELF; wrap in bash (CONFIG_SHELL).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_silo_llnl")
        self.run(f"{bash} -c '{bin_path}'", env="conanrun")
