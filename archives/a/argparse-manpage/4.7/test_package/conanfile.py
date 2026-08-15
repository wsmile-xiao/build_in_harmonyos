#!/usr/bin/env python3
"""Conan test_package for argparse-manpage.

Runs test_argparse_manpage.py which invokes the argparse-manpage
tool to generate a man page from a Python argparse parser and
verifies the output contains expected sections.
"""
import os

from conan import ConanFile


class ArgparseManpageTestConan(ConanFile):
    """test_package for argparse-manpage application package."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("python3 test_argparse_manpage.py", env="conanrun")
