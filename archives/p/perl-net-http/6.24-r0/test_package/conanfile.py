#!/usr/bin/env python3
"""Conan test_package — Perl module Net::HTTP 6.24.

Verifies that the Perl module can be loaded after installation.
"""
import os

from conan import ConanFile


class PerlnethttpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the Perl module can be loaded
        self.run("perl -MNet::HTTP -e 'print \"Net::HTTP loaded OK\\n\"'", env="conanrun")
