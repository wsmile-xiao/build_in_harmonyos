#!/usr/bin/env python3
"""Conan test_package for freeunit 1.36.0 (unitd daemon)."""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class FreeunitTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["freeunit"].package_folder
        bin_path = os.path.join(package_folder, "bin", "unitd")
        assert os.path.isfile(bin_path), f"unitd binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test_freeunit.sh")
            # HMBS injects SHELL=/bin/sh; avoid hard-coded `bash`. Run from a
            # writable cwd (TMPDIR, injected by HMBS) instead of the HMDFS
            # package folder.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            actual_command = f'"{shell}" "{test_script}" "{bin_path}"'
            self.run(actual_command, env="conanrun", cwd=cwd)
            # test_freeunit.sh runs 2 assertions (--version / -h), both must
            # pass; self.run raises on a non-zero script exit so the marker
            # below is only emitted when the packaged binary really works.
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": actual_command,
                "discovered": 2,
                "passedCount": 2,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"unitd is not an ELF binary: {magic!r}"
            self.output.info(f"unitd binary exists and has ELF magic: {bin_path}")
