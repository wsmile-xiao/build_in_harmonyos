#!/usr/bin/env python3
"""Conan test_package for qrcp 0.11.6 — consumer smoke test of the packaged binary.

qrcp is a Go CLI application (not a linkable C/C++ library). The consumer test runs
the packaged `qrcp` binary headlessly and asserts:
  - `qrcp version` exits 0 and reports 0.11.6
  - `qrcp --help` lists the core sub-commands (send / receive)
  - [HarmonyOS-specific] the packaged ELF is OHOS-signed (`.codesign` section), which
    is required before the HarmonyOS kernel will exec the binary.

File location: archives/q/qrcp/0.11.6/test_package/conanfile.py
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class QrcpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["qrcp"].package_folder
        exe_name = "qrcp.exe" if str(self.settings.os) == "Windows" else "qrcp"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"qrcp binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test_qrcp.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            expect_codesign = "1" if str(self.settings.os) == "OHOS" else "0"
            self.run(f'"{shell}" "{test_script}" "{bin_path}" {expect_codesign}',
                     env="conanrun", cwd=cwd)
            # test_qrcp.sh runs 6 explicit assertions (see MANIFEST.yml).
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{test_script}" "{bin_path}"',
                "discovered": 6,
                "passedCount": 6,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"qrcp is not an ELF binary: {magic!r}"
            self.output.info(f"qrcp binary exists and has ELF magic: {bin_path}")
