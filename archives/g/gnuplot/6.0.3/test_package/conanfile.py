#!/usr/bin/env python3
"""Conan test_package for gnuplot 6.0.3 — L1 test.

Verifies that the gnuplot binary is installed and can report its version
and generate a simple plot. gnuplot is a command-line plotting tool (application).
"""
import os

from conan import ConanFile


class GnuplotTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("bash test.sh", env="conanrun")
