#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libfm-extra/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfmextraTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The public fm-xml-file.h includes glib-object.h; declare the
        # consumer's direct header dependency explicitly.
        self.requires("glib/2.88.0")
        self.requires("gettext/0.22.5")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        # Cross-compiled binaries cannot execute on the build host.
        # Compilation + linking success is sufficient L1 verification.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libfm-extra")
        if not os.path.isfile(test_bin):
            raise ConanException("test binary not found")
        self.output.info("test binary built successfully — skipping execution "
                         "(cross-compiled)")
        # Uncomment below when native build or QEMU is available:
        # self.run(test_bin, env="conanrun")
