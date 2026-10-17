#!/usr/bin/env python3
"""Conan test_package for lcdf-typetools — verifies the binaries work.

L1 official test: runs `cfftot1 --version`, `otfinfo --version`,
and `t1lint --version` to verify the binaries are correctly built.
"""
import os

from conan import ConanFile


class LcdfTypetoolsTestConan(ConanFile):
    settings = "os", "arch", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        # conanrun env includes the package's bin/ in PATH
        self.run("cfftot1 --version", env="conanrun")
        self.run("otfinfo --version", env="conanrun")
        self.run("t1lint --version", env="conanrun")
