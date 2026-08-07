#!/usr/bin/env python3
"""Conan test_package for mini_httpd — verify the installed binary works.

mini_httpd is a command-line tool. The test runs `mini_httpd -V` to verify
the binary is correctly installed and functional.
"""
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class MiniHttpdTestConan(ConanFile):
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
        # Skip test execution in cross-compilation: target arch binary
        # cannot run on x86_64 CI workers
        if cross_building(self):
            return

        # Run the installed binary directly to verify it works
        self.run("mini_httpd -V", env="conanrun")

        # Also run the CMake-built test
        cmake = CMake(self)
        cmake.test()
