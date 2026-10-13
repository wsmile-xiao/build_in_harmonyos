#!/usr/bin/env python3
"""Conan test_package for tetradraw 2.0.3 — smoke-Tests binary tools."""
import os

from conan import ConanFile


class TetradrawTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        # Keep generator/build artifacts out of the archive source tree
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["tetradraw"].package_folder, "bin")
        for name in ("tetradraw", "tetraview"):
            assert os.path.isfile(os.path.join(bin_dir, name)), f"missing {name}"
        test_script = os.path.join(self.source_folder, "test_tetradraw.sh")
        os.chmod(test_script, 0o755)
        self.run(f'sh "{test_script}" "{bin_dir}"', env="conanrun")
