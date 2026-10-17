#!/usr/bin/env python3
"""Conan test_package for libvecpf - the L1 consumer test.

Builds test_vecpf.c against the *installed* package (headers + shared library
resolved through CMakeDeps) and executes it.  The test calls only the public
API declared in the installed <vecpf.h> and compares the output against
hand-computed expectations.

CI runs this automatically via `conan create`.

File location: archives/l/libvecpf/1.1.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibvecpfTestConan(ConanFile):
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
        # Run both binaries explicitly (rather than through ctest) so their
        # output ends up in the conan create log.
        for name in ("test_vecpf", "test_vecpf_cxx"):
            binary = os.path.join(self.cpp.build.bindirs[0], name)
            self.run(binary, env="conanrun")
