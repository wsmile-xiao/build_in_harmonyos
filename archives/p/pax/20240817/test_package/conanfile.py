#!/usr/bin/env python3
"""Conan test_package for pax 20240817.

Tests that pax binary can create, list, and extract archives.
"""
import os

from conan import ConanFile



class PaxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Find pax binary in the package
        pax_bin = os.path.join(self.package_folder, "bin", "pax")
        if not os.path.isfile(pax_bin):
            pax_bin = os.path.join(self.package_folder, "bin", "paxpax")
        if not os.path.isfile(pax_bin):
            pax_bin = "pax"

        test_dir = os.path.join(self.build_folder, "pax_test")
        os.makedirs(test_dir, exist_ok=True)

        # Create test files
        with open(os.path.join(test_dir, "hello.txt"), "w") as f:
            f.write("hello world\n")
        os.makedirs(os.path.join(test_dir, "subdir"), exist_ok=True)
        with open(os.path.join(test_dir, "subdir", "file.txt"), "w") as f:
            f.write("nested\n")

        # Test 1: Create archive
        # pax may exit with code 1 due to uid/gid warnings on OHOS
        # (large uids don't fit in ustar header), but archive is still created
        archive = os.path.join(test_dir, "test.tar")
        self.run(f'{pax_bin} -w -x ustar -f "{archive}" .',
                 cwd=test_dir, env="conanrun", ignore_errors=True)
        assert os.path.isfile(archive), "Archive was not created"

        # Test 2: List archive
        self.run(f'{pax_bin} -f "{archive}"', env="conanrun")

        # Test 3: Extract archive
        extract_dir = os.path.join(self.build_folder, "pax_extract")
        os.makedirs(extract_dir, exist_ok=True)
        self.run(f'{pax_bin} -r -f "{archive}"', cwd=extract_dir, env="conanrun")

        # Verify extracted content
        extracted_file = os.path.join(extract_dir, "hello.txt")
        assert os.path.isfile(extracted_file), "Extracted file hello.txt not found"
        with open(extracted_file) as f:
            content = f.read().strip()
        assert content == "hello world", f"Content mismatch: got '{content}'"
