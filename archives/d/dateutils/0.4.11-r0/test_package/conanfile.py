#!/usr/bin/env python3
"""Conan test_package for dateutils — verify CLI tools work."""
import os
from conan import ConanFile


class DateutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the installed binaries are usable
        bindir = os.path.join(self.dependencies["dateutils"].package_folder, "bin")
        assert os.path.isdir(bindir), f"bin directory not found: {bindir}"

        # Test key binaries exist
        expected_bins = [
            "dateadd", "dateconv", "datediff", "dategrep", "dateround",
            "dateseq", "datesort", "datetest", "datezone", "strptime",
        ]
        for bin_name in expected_bins:
            bin_path = os.path.join(bindir, bin_name)
            assert os.path.isfile(bin_path), f"Binary not found: {bin_path}"

        # Smoke test: run one binary with --version
        self.run(f"{os.path.join(bindir, 'datediff')} --version", env="conanrun")
        # Smoke test: run another with a basic operation (date first, then duration)
        self.run(f"{os.path.join(bindir, 'dateadd')} 2020-01-01 1d", env="conanrun")
