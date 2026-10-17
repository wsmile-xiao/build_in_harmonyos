#!/usr/bin/env python3
"""Conan test package for libcxx-serial 1.2.1 (R34 consumer smoke).

Links the packaged library and runs a real API exercise on the target:
serial::list_ports() (sysfs tty enumeration through list_ports_linux.cc)
plus the public bytesize/parity/stopbits/flowcontrol enums.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        test_exe = os.path.join(self.cpp.build.bindir, "test_package")
        if not os.path.isfile(test_exe):
            raise ConanException(f"test executable not found: {test_exe}")
        self.run(test_exe, env="conanrun")
