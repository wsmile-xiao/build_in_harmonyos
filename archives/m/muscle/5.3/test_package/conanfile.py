#!/usr/bin/env python3
"""test_package for MUSCLE 5.3 — verifies the muscle binary.

On OHOS, unsigned ELF binaries cannot be executed locally (security
mechanism). The test falls back to ELF magic verification when the
binary cannot be run.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MuscleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["muscle"].package_folder
        bin_path = os.path.join(package_folder, "bin", "muscle")
        assert os.path.isfile(bin_path), f"muscle binary not found: {bin_path}"

        # Verify ELF magic bytes (always works, even without signing)
        with open(bin_path, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", f"muscle is not an ELF binary: {magic!r}"
        self.output.info(f"muscle binary exists and has ELF magic: {bin_path}")

        # Try to run the binary — on OHOS, unsigned binaries fail with
        # "Operation not permitted". This is expected; CI signs the binary
        # via sign.sh before running the test.
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'{bash} "{test_script}"', env="conanrun")
