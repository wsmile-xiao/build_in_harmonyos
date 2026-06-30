#!/usr/bin/env python3
"""Conan test_package — fonts-encodings 1.1.0

Data-only package test: verifies that encoding data files exist
in the package's share/fonts/X11/encodings/ directory.
"""
import os

from conan import ConanFile


class FontsEncodingsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder from the dependency
        pkg = self.dependencies["fonts-encodings"]
        pkg_root = pkg.package_folder

        encodings_dir = os.path.join(pkg_root, "share", "fonts", "X11", "encodings")

        # Check encodings.dir exists
        encodings_dir_file = os.path.join(encodings_dir, "encodings.dir")
        assert os.path.exists(encodings_dir_file), \
            f"encodings.dir not found at {encodings_dir_file}"

        # Check at least some .enc.gz files exist
        enc_files = [f for f in os.listdir(encodings_dir) if f.endswith(".enc.gz")]
        assert len(enc_files) > 0, \
            f"No .enc.gz files found in {encodings_dir}"

        # Check large/ subdirectory
        large_dir = os.path.join(encodings_dir, "large")
        assert os.path.isdir(large_dir), \
            f"large/ subdirectory not found at {large_dir}"

        large_enc_files = [f for f in os.listdir(large_dir) if f.endswith(".enc.gz")]
        assert len(large_enc_files) > 0, \
            f"No .enc.gz files found in {large_dir}"

        # Check large/encodings.dir exists
        large_encodings_dir = os.path.join(large_dir, "encodings.dir")
        assert os.path.exists(large_encodings_dir), \
            f"large/encodings.dir not found at {large_encodings_dir}"

        self.output.info(f"fonts-encodings test passed: {len(enc_files)} small + {len(large_enc_files)} large encodings found")
