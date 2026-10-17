#!/usr/bin/env python3
"""Conan test_package for asciitex 0.32 — application (CLI tool).

R34: test_package executes the asciitex binary.
The test_asciitex.sh script runs `asciitex -v` to verify
the binary is installed and functional.
"""
import os
from conan import ConanFile


class AsciitexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Execute the asciitex binary to verify the package
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test_asciitex.sh", env="conanrun")
