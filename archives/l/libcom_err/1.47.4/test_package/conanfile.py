#!/usr/bin/env python3
"""Conan test_package — libcom_err 1.47.4 consumer smoke test.

Builds test_com_err.c against the installed libcom_err (com_err::com_err)
and executes it. The C binary runs 5 real API checks (see test_com_err.c)
and emits the HMBS_TEST_PACKAGE_RESULT marker itself with discovered /
passedCount taken from its own executed-check counters, so the numbers are
produced by the actual test command.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibcomerrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        self.run("./test_com_err", env="conanrun")
