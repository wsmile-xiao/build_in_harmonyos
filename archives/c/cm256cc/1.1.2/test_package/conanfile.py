#!/usr/bin/env python3
"""Conan test_package — runs the upstream cm256_test binary and a real API consumer."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Cm256ccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) Run the upstream test binary shipped in the package bin/
        #    (4 scenarios; exits non-zero on any failure).
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        upstream = os.path.join(bindir, "cm256_test")
        if not os.path.isfile(upstream):
            raise Exception(f"upstream test binary not found: {upstream}")
        self.run(upstream, env="conanrun")

        # 2) Run the consumer program that calls the CM256 API directly.
        consumer = os.path.join(self.cpp.build.bindirs[0], "consumer")
        self.run(consumer, env="conanrun")
