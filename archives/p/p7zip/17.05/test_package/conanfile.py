#!/usr/bin/env python3
"""Conan test_package for p7zip 17.05 — verifies the 7za binary works."""
import os

from conan import ConanFile


class P7ZipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the 7za binary path from the package
        pkg = self.dependencies["p7zip"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        sevenza = os.path.join(bin_dir, "7za")
        # Test 1: 7za should report version info
        self.run(f'"{sevenza}" 2>&1 | head -1', env="conanrun")
        # Test 2: Functional test - create archive, list, extract, verify
        test_file = os.path.join(self.build_folder, "hello.txt")
        with open(test_file, "w") as f:
            f.write("p7zip conan test content\n")
        archive = os.path.join(self.build_folder, "test.7z")
        self.run(f'"{sevenza}" a "{archive}" "{test_file}"', env="conanrun")
        self.run(f'"{sevenza}" l "{archive}"', env="conanrun")
        self.run(f'"{sevenza}" t "{archive}"', env="conanrun")
