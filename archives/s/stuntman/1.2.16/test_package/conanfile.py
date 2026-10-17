#!/usr/bin/env python3
"""Conan test_package for stuntman 1.2.16 — binary tool smoke test.

Verifies that the stunclient binary is installed and runs correctly.
"""
import os

from conan import ConanFile


class StuntmanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the stunclient binary in the package
        bin_path = os.path.join(self.dependencies["stuntman"].package_folder, "bin", "stunclient")
        if not os.path.exists(bin_path):
            for root, dirs, files in os.walk(self.dependencies["stuntman"].package_folder):
                if "stunclient" in files:
                    bin_path = os.path.join(root, "stunclient")
                    break
        # Run stunclient --help and verify output contains expected text
        # grep returns 0 only if binary runs AND produces "STUNCLIENT" output
        # When bin/ is removed (L1e), binary is missing → grep fails → test fails (R34)
        self.run(f'"{bin_path}" --help 2>&1 | grep -q STUNCLIENT', env="conanrun")
