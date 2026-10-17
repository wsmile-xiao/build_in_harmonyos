#!/usr/bin/env python3
"""Conan test_package for tftp-hpa 5.2 — verify the tftp client binary works."""

from conan import ConanFile


class TftpHpaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must exercise the actual binary
        self.run("tftp -V", env="conanrun")
