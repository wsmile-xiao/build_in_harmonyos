#!/usr/bin/env python3
"""Consumer test for ytnef/2.1.2.

Builds a small C program that links the packaged `libytnef` and decodes a real
TNEF stream, then additionally runs the installed command line tools, so the
library half and the CLI half of the package are both verified.
"""
import base64
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import load


class YtnefTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # keep the CMake build tree out of the recipe folder
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _materialise_fixture(self):
        """Write the base64 encoded TNEF fixture next to the test binary.

        The fixture is a real `winmail.dat`-style stream but is stored as text:
        a merge-request diff carries no binary patch data, so shipping the raw
        `.tnef` file would make the CI `checkout-pr` step fail with
        "missing binary patch data".
        """
        encoded = load(self, os.path.join(self.source_folder, "one-file.tnef.b64"))
        with open(os.path.join(self.build_folder, "one-file.tnef"), "wb") as fh:
            fh.write(base64.b64decode(encoded))

    def test(self):
        self._materialise_fixture()
        cmake = CMake(self)
        cmake.test()                       # library API assertions (test.c)
        # the installed command line tools must be packaged and runnable (R38)
        for tool in ("ytnef", "ytnefprint"):
            self.run("{} -h".format(tool), env="conanrun")
