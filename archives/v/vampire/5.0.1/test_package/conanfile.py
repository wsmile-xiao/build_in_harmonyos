#!/usr/bin/env python3
"""Conan test_package for vampire 5.0.1 — smoke test (run --version)."""
import os

from conan import ConanFile


class VampireTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build needed — vampire is a pre-built binary
        pass

    def test(self):
        # L2 smoke test: run vampire --version to verify the binary works
        vampire_pkg = self.dependencies["vampire"]
        vampire_bin = os.path.join(vampire_pkg.package_folder, "bin", "vampire")
        self.output.info(f"Running smoke test: {vampire_bin} --version")
        self.run(f'"{vampire_bin}" --version', env="conanrun")
