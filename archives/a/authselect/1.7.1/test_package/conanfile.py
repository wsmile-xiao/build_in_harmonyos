#!/usr/bin/env python3
"""Test package for authselect — CLI application consumer."""
from conan import ConanFile


class AuthselectTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # authselect is an application package.  Execute the real CLI
        # consumer test script (test_authselect.sh) inside the conanrun
        # environment so PATH points at the installed package bin dir.
        self.run("sh test_authselect.sh", env="conanrun")