#!/usr/bin/env python3
"""test_package for pngcrush — compiles and runs the C functional test.

The test (test.c) writes a tiny PNG, drives the installed pngcrush binary
to losslessly recompress it, and verifies the result is still a valid PNG.
"""
from conan import ConanFile


class PngcrushTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile the C test that drives the installed pngcrush binary.
        self.run("/data/service/hnp/bin/clang -o test test.c")

    def test(self):
        self.run("./test", env="conanrun")
