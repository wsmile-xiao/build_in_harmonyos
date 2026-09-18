#!/usr/bin/env python3
"""Conan test_package for msquic 2.6.1 (L1 smoke test).

Runs the real public API: MsQuicOpen2 → GetParam(TLS_PROVIDER) →
RegistrationOpen (spawns musl pthread workers) → ConfigurationOpen →
close everything. The __OHOS__ block prints the harmony-specific
verification line required by rule12.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class MsquicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Direct execution fallback for visibility:
        # self.run(os.path.join(self.cpp.build.bindirs[0], "test_msquic"), env="conanrun")
