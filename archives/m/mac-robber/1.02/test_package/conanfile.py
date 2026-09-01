#!/usr/bin/env python3
"""Conan test_package — mac-robber 1.02 (forensics CLI, executable).

test.sh constructs an auditable file tree (regular file, empty file,
subdirectory, symlink) in a temp dir, then runs the real mac-robber
binary against it and verifies the 'time machine' body-file output.

HMBS_TEST_PACKAGE_RESULT is emitted by test.sh as machine evidence.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MacRobberTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["mac-robber"].package_folder
        bin_path = os.path.join(package_folder, "bin", "mac-robber")
        assert os.path.isfile(bin_path), f"mac-robber binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', cwd=cwd)
            # HMBS_TEST_PACKAGE_RESULT emitted by test.sh.
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"mac-robber is not an ELF binary: {magic!r}"
            self.output.info(f"mac-robber binary exists and has ELF magic: {bin_path}")
