#!/usr/bin/env python3
"""Conan test_package for msfconsole 4.11.7.

msfconsole is an application package (CLI tools + Ruby scripts).
The test verifies that the compiled C tools (time-key, stat-key)
work correctly and the msfconsole Ruby script is installed.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MsfconsoleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: substantively test the package's binaries

        # Run CTest (test_msfconsole invokes time-key and stat-key)
        cmake = CMake(self)
        cmake.test()

        # Also directly run the package's C tools
        # time-key: no args → outputs hex time key, exits 0
        self.run("time-key", env="conanrun")

        # stat-key: no args → usage error, exits 1
        # The expected failure is verified by test_msfconsole (test.c) via
        # system("stat-key") with return-code check.
        # Here we just confirm stat-key is in PATH.
        self.run("which stat-key", env="conanrun")

        # Verify msfconsole Ruby script exists in bin/
        self.run("test -f \"$(which msfconsole)\"", env="conanrun")
