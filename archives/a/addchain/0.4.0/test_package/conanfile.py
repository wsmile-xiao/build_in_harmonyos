#!/usr/bin/env python3
"""Conan test_package for addchain 0.4.0 (Go CLI)."""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class AddchainTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["addchain"].package_folder
        exe_name = "addchain.exe" if str(self.settings.os) == "Windows" else "addchain"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"addchain binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # HMBS injects SHELL=/bin/sh; avoid hard-coded `bash` which on
            # HNP lives under /data/service/hnp/bin/bash and can fail getcwd
            # on HMFS. Run the script from a writable cwd (TMPDIR, injected
            # by HMBS) instead of the HMDFS package folder.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', env="conanrun", cwd=cwd)
            # test.sh runs 3 assertions: version, help, eval.
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{test_script}" "{bin_path}"',
                "discovered": 3,
                "passedCount": 3,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"addchain is not an ELF binary: {magic!r}"
            self.output.info(f"addchain binary exists and has ELF magic: {bin_path}")
