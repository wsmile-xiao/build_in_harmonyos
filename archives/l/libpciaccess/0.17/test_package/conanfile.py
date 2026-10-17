#!/usr/bin/env python3
"""Conan consumer test — libpciaccess 0.17 (CMake).

R34: test_package must call the library API, not just print.
Both consumer binaries call pci_get_strings/pci_system_init and are
executed in test().
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibpciaccessTestConan(ConanFile):
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
        bindir = self.cpp.build.bindirs[0]
        for executable in ("test_libpciaccess", "test_libpciaccess_harmonyos"):
            self.run(os.path.join(bindir, executable), env="conanrun")
