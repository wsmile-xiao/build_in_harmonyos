#!/usr/bin/env python3
"""Conan test_package — usrsctp 0.9.5.0 L1 consumer test.

Builds test.c against the packaged usrsctp library (CMakeDeps) and runs the
resulting test_usrsctp binary, which exercises usrsctp_init/socket/bind/
close/finish (R34: real API usage, not a print-only shell).

File location: archives/u/usrsctp/0.9.5.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UsrsctpTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_usrsctp')}", env="conanrun")
