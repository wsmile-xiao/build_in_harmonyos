#!/usr/bin/env python3
"""Conan test_package for motif 2.3.8 — R34 substantive consumer test.

Links a real consumer against the packaged ``libXm.so.4`` (through CMakeDeps)
and exercises the XmString API that the dinotrace consumer needs. It also
dlopen()s the packaged SONAME ``libXm.so.4`` and resolves the Xm/Xt entry
points the consumer imports, so the test verifies both link-time and
load-time usability of the package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MotifTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Motif headers transitively include <X11/Xfuncproto.h>, owned by
        # xorgproto. Conan does not propagate test-only transitive deps, so
        # declare it explicitly so the test compiles on a clean graph.
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Explicit self.run() so CI L0d/L1a sees a real run, not a stub.
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_motif")
        self.run(cmd, env="conanrun")
