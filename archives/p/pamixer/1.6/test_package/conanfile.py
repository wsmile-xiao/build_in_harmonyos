#!/usr/bin/env python3
"""Conan test_package for pamixer 1.6.

Verifies that the pamixer binary is present and functional.
R34: test genuinely depends on the tested package — if the pamixer
binary is missing (L1e destructive test), this test fails.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PamixerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass  # No build needed — we test the installed binary

    def test(self):
        # R34: test must actually depend on the tested package.
        # We verify the pamixer binary exists and is a valid ELF.
        # If the binary is missing (L1e destructive test), this fails.
        pamixer_bin = os.path.join(
            self.dependencies["pamixer"].package_folder, "bin", "pamixer")

        script = os.path.join(self.source_folder, "test_pamixer.sh")
        self.run(f'bash "{script}" "{pamixer_bin}"')
