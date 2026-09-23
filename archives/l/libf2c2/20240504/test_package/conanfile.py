#!/usr/bin/env python3
"""Conan test_package — libf2c2 20240504 (Conan L1 consumer test).

Builds two consumers against the installed package and runs both:

* test_main    — ordinary C program: calls the intrinsic, character-string
                 and list-directed I/O entry points declared in f2c.h and
                 checks their results, including a file round trip.
* test_startup — f2c-translated program: defines MAIN__ and has no main() of
                 its own, so the entry point, f_init() and the atexit(f_exit)
                 flush come from the library.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libf2c2TestConan(ConanFile):
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
        # Executed directly rather than through cmake.test(): the CI stub-test
        # gate (L0d) decides on the presence of an explicit execution call in
        # this method.  Running the consumers here also puts their per-check
        # output into the CI log.
        self.run("./test_main", env="conanrun")
        self.run("./test_startup", env="conanrun")
