#!/usr/bin/env python3
"""Conan test_package — sword/1.9.0 L1 consumer test (R34: real API calls,
rc-gated execution of test.cpp which asserts libsword behaviour)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SwordTestConan(ConanFile):
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
        if not os.environ.get("TMPDIR"):
            os.environ["TMPDIR"] = os.path.join(self.build_folder, "tmp")
        # Direct execution: non-zero rc (any failed CHECK in test.cpp) fails
        # the test; no pass-only/print-only stub (PF3/L1e honest).
        exe = os.path.join(self.cpp.build.bindirs[0], "test_sword")
        if not os.path.isabs(exe):
            exe = "./" + exe
        self.run(f'"{exe}"', env="conanrun")
