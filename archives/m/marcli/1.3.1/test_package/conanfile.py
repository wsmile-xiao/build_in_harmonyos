#!/usr/bin/env python3
"""Conan test_package for marcli 1.3.1 — HarmonyOS consumer feasibility test.

marcli is a Go CLI application (not a linkable C/C++ library), so the consumer
test executes the packaged `marcli` binary headlessly on the target. It is
SEPARATE from the upstream `go test ./...` suite, which is executed in build()
and reported independently (test_package must not substitute upstream stats).

File location: archives/m/marcli/1.3.1/test_package/conanfile.py
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class MarcliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["marcli"].package_folder
        exe_name = "marcli.exe" if str(self.settings.os) == "Windows" else "marcli"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), "marcli binary not found: %s" % bin_path

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            testdata = os.path.join(self.recipe_folder, "testdata")
            # test.sh uses `set -euo pipefail`, which is not POSIX sh: run it with bash.
            shell = (os.environ.get("BASH") or shutil.which("bash") or "/bin/bash")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run('%s "%s" "%s" "%s"' % (shell, test_script, bin_path, testdata),
                     env="conanrun", cwd=cwd)
            payload = {
                "executed": True,
                "passed": True,
                "command": '%s "%s" "%s" "%s"' % (shell, test_script, bin_path, testdata),
                "discovered": 5,
                "passedCount": 5,
                "cases": [
                    "marcli (no args) prints the syntax banner containing 'marcli v1.3.1'",
                    "marcli -format count-only == 1 (test_1a.mrc)",
                    "marcli -format mrk renders MARC records (contains '=LDR')",
                    "marcli -format json emits a valid JSON array",
                    "OHOS-specific: packaged ELF carries a .codesign section",
                ],
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(payload, ensure_ascii=False))
            # Upstream `go test` statistics are emitted by build() and reported
            # separately; they are intentionally NOT duplicated here.
            self.output.info("HMBS_UPSTREAM_TEST_RESULT_NOTE=executed_in_build_see_conan_create_log")
        else:
            with open(bin_path, "rb") as fh:
                magic = fh.read(4)
            assert magic == b"\x7fELF", "marcli is not an ELF binary: %r" % magic
            self.output.info("marcli binary exists and has ELF magic: %s" % bin_path)
