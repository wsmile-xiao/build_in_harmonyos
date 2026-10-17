#!/usr/bin/env python3
"""Test package for codecov-cli — verifies the CLI tool works.

L1 test: runs `codecov --version` to verify the installed binary works.
R34: test must actually invoke the packaged binary (not a stub).
"""
from conan import ConanFile


class CodecovCliTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually invoke the packaged codecov binary
        self.run("codecov --version", env="conanrun")
