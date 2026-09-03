#!/usr/bin/env python3
"""Conan test_package for libxmu 1.3.1 — L1 official test (R34: substantive).

Exercises XmuCompareISOLatin1() from libXmuu (Xt-independent subset of libXmu),
the same API the upstream "Lower" unit test verifies.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibxmuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libXmu headers transitively include X11/Xfuncproto.h, owned by
        # xorgproto. Conan does not propagate test-only transitive deps,
        # so declare it explicitly so the test compiles on a clean graph.
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Explicit self.run() so CI L0d does not flag this as a stub test.
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_libxmu")
        self.run(cmd, env="conanrun")
