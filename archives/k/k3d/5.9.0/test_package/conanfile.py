#!/usr/bin/env python3
"""Conan test_package for k3d 5.9.0 (Go CLI)."""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class K3dTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["k3d"].package_folder
        bin_path = os.path.join(package_folder, "bin", "k3d")
        assert os.path.isfile(bin_path), f"k3d binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # HMBS injects SHELL=/bin/sh; run from a writable cwd (TMPDIR).
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            # The build() method of the k3d recipe may leave os.environ's
            # TMPDIR pointing at a go-work tmp dir that it never created;
            # ensure the cwd exists before spawning test.sh, otherwise
            # self.run(..., cwd=cwd) raises FileNotFoundError.
            os.makedirs(cwd, exist_ok=True)
            cmd = f'"{shell}" "{test_script}" "{bin_path}"'
            self.run(cmd, env="conanrun", cwd=cwd)
            # test.sh runs 2 assertions: version string + --help.
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": cmd,
                "discovered": 2,
                "passedCount": 2,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"k3d is not an ELF binary: {magic!r}"
            self.output.info(f"k3d binary exists and has ELF magic: {bin_path}")
