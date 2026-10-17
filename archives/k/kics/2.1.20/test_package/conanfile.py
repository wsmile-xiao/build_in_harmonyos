#!/usr/bin/env python3
"""Conan test_package for kics 2.1.20 — HarmonyOS consumer feasibility test.

kics is a Go CLI application (not a linkable C/C++ library). The consumer test
runs the packaged `kics` binary headlessly on the target and asserts:
  - `kics version` exits 0 and reports v2.1.20 (ELF signed + embedded constants OK)
  - a real `kics scan` on a minimal terraform file produces a JSON report
    (exercises the go:embed'd query assets on OHOS — proves consumer feasibility)

This is the required HarmonyOS-specific consumer use-case test. It is SEPARATE
from the upstream `go test ./...` suite, which is executed in build() and reported
independently (test_package must not substitute upstream test statistics).

File location: archives/k/kics/2.1.20/test_package/conanfile.py
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class KicsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["kics"].package_folder
        exe_name = "kics.exe" if str(self.settings.os) == "Windows" else "kics"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"kics binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # HMBS injects SHELL=/bin/sh; run the script from a writable cwd
            # (TMPDIR) instead of the HMDFS package folder.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', env="conanrun", cwd=cwd)
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{test_script}" "{bin_path}"',
                "discovered": 2,
                "passedCount": 2,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            # NOTE: upstream `go test ./...` statistics are emitted by build() and
            # reported separately; they are intentionally NOT duplicated here.
            print("HMBS_UPSTREAM_TEST_RESULT_NOTE=executed_in_build_see_conan_create_log")
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"kics is not an ELF binary: {magic!r}"
            self.output.info(f"kics binary exists and has ELF magic: {bin_path}")
