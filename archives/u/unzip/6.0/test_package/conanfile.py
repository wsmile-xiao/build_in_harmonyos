#!/usr/bin/env python3
"""Conan test_package for unzip 6.0 — verifies the unzip binary works.

Tests that the unzip executable can extract a ZIP archive correctly.
This is a consumer-side test (R34: test must substantially depend on the
tested package by executing its binary).
"""
import os

from conan import ConanFile


class UnzipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the unzip binary from the package (Conan 2.x API)
        dep = self.dependencies["unzip"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        unzip_bin = os.path.join(bin_dir, "unzip")

        # Create a test ZIP file using Python zipfile
        import zipfile
        test_dir = self.build_folder
        os.makedirs(test_dir, exist_ok=True)

        zip_path = os.path.join(test_dir, "test_archive.zip")
        expected_content = "Hello from unzip test!\n"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("hello.txt", expected_content)

        # Create extraction directory
        extract_dir = os.path.join(test_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        # Run the test script (R34: substantial dependency on tested package)
        test_script = os.path.join(self.source_folder, "test_unzip.sh")
        os.chmod(test_script, 0o755)
        self.run(f'{test_script} "{unzip_bin}" "{zip_path}" "{extract_dir}"', env="conanrun")
