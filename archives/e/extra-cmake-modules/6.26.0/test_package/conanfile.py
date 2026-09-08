#!/usr/bin/env python3
"""Conan test_package — extra-cmake-modules 6.26.0 L1 test.

R34: test_package must genuinely exercise the tested package. ECM is a
cmake-only module package, so consuming it means find_package(ECM) and using
one of its CMake macros. This test loads ECMFindModuleHelpers, calls
ecm_find_package_version_check(), asserts ECM_VERSION / ECM_MODULE_DIR, and
compiles+runs a C++ program that validates those values at runtime.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestExtraCMakeModulesConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        ecm_prefix = self.dependencies["extra-cmake-modules"].package_folder
        cmake.configure(variables={"ECM_PACKAGE_PREFIX": ecm_prefix})
        cmake.build()

    def test(self):
        test_program = os.path.join(self.cpp.build.bindir, "test_ecm")
        self.run(test_program, env="conanrun")
