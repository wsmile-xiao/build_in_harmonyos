#!/usr/bin/env python3
"""Consumer test for libe-book/0.1.4.

Builds the C++ consumer test against the installed package and runs it under
the package's runtime environment.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibebookTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libe-book's public headers expose librevenge types
        # (RVNGInputStream / RVNGTextInterface), so the consumer needs it on
        # the include path and link line as well; the librevenge package
        # bundles the stream and generators libraries, which the test uses.
        self.requires("librevenge/0.0.5")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at
        # a /usr/local/lib whose incompatible libxml2.so.16 breaks the
        # SDK's lld on every link — CI-021 build #48068).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        # Verdict by direct execution under conanrun: libxml2 is a shared
        # dependency and ctest does not inherit conan's runtime environment
        # (libabw / libodfgen / libetonyek precedent).
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libe_book"),
                 env="conanrun")
