#!/usr/bin/env python3
"""Conan test_package for ECM 6.20.0 — L1 test.

Verifies that ECM CMake modules are correctly installed and discoverable
via find_package(ECM). The test compiles a C++ program that includes
ECM macros and asserts the installed version matches the expected one.
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestECMConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        ecm_prefix = self.dependencies["ecm"].package_folder
        cmake.configure(variables={"ECM_PACKAGE_PREFIX": ecm_prefix})
        cmake.build()

    def test(self):
        test_program = os.path.join(self.cpp.build.bindir, "test_ecm")
        self.run(test_program, env="conanrun")
