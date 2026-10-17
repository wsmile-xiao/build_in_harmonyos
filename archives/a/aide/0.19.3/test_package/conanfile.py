#!/usr/bin/env python3
"""Conan test_package for aide 0.19.3 — binary tool smoke test.

Verifies that the aide binary is installed and runs correctly by executing
test.sh, which genuinely runs `aide --version` and asserts the version
string (R34: no stub tests allowed).
"""
import os

from conan import ConanFile


class AideTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Execute test.sh with the Conan run environment so the packaged
        # aide binary (and its dynamic libgcrypt/libgpg-error deps) resolve
        # from the package layout.
        self.run("sh test.sh", env="conanrun")
