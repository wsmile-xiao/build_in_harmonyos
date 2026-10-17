#!/usr/bin/env python3
"""test_package for execline — compiles a C program calling execline APIs."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class ExeclineTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # execline depends on skalibs; test.c directly includes skalibs headers
        self.requires("skalibs/2.15.1.0")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly to substantively exercise execline APIs (R34).
        # L0d requires self.run() in test() — cmake.test() alone is not sufficient.
        self.run("./test_execline", env="conanrun")
