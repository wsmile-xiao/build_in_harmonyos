#!/usr/bin/env python3
"""Conan test_package for bam 0.5.1 — verifies bam binary works.

bam is a build tool (not a library), so we test by:
1. Running bam --help to verify the binary executes
2. Creating a simple C project with a bam.lua script and building it
"""
import os

from conan import ConanFile


class BamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        import shutil
        for f in ("bam.lua", "hello.c"):
            try:
                shutil.copy(os.path.join(self.source_folder, f),
                            os.path.join(self.build_folder, f))
            except shutil.SameFileError:
                pass

    def test(self):
        bam_bin = os.path.join(self.dependencies["bam"].package_folder, "bin", "bam")

        # Test 1: bam --help (verifies binary executes correctly)
        self.run(f'"{bam_bin}" --help')

        # Test 2: Build a simple C project using bam
        self.run(f'"{bam_bin}" -v', cwd=self.build_folder)

        # Verify the compiled output exists
        assert os.path.exists(os.path.join(self.build_folder, "hello")), \
            "bam failed to produce 'hello' binary"
