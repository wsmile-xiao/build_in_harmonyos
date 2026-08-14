#!/usr/bin/env python3
"""Conan test_package — perl-stream-buffered 0.03-r5

Tests that Stream::Buffered can be loaded and used to buffer bytes.
"""
import os
import glob

from conan import ConanFile


class PerlStreamBufferedTestConan(ConanFile):
    # L0p: OHOS profile requires all four settings
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Stream/Buffered.pm in the package folder
        pkg = self.dependencies["perl-stream-buffered"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Buffered.pm"), recursive=True)
        if not pm_files:
            raise Exception("Stream/Buffered.pm not found in package")
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))
        test_script = os.path.join(self.recipe_folder, "run_test.sh")
        self.run(f'sh "{test_script}" "{lib_dir}"')
