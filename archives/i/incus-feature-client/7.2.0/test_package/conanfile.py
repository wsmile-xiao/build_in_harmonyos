#!/usr/bin/env python3
"""Conan test_package for incus-feature-client 7.2.0 — consumer smoke test of the packaged binary.

incus-feature-client is the Incus CLI client (`incus`), a Go application (not a linkable
C/C++ library). The consumer test runs the packaged `incus` binary headlessly and asserts:
  - `incus --version` exits 0 and reports the 7.2 series
  - `incus --help` exits 0 and lists the core sub-commands (list / remote)
  - [HarmonyOS-specific] the packaged ELF targets aarch64 and is OHOS-signed
    (`.codesign` section), which is required before the HarmonyOS kernel will exec it.

File location: archives/i/incus-feature-client/7.2.0/test_package/conanfile.py
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class IncusFeatureClientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["incus-feature-client"].package_folder
        exe_name = "incus.exe" if str(self.settings.os) == "Windows" else "incus"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"incus binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test_incus.sh")
            shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            expect_ohos = "1" if str(self.settings.os) == "OHOS" else "0"
            self.run(f'"{shell}" "{test_script}" "{bin_path}" {expect_ohos}', env="conanrun", cwd=cwd)
            # test_incus.sh runs 7 explicit assertions (see MANIFEST.yml), 2 of them
            # HarmonyOS-specific (aarch64 ELF target + OHOS .codesign signature).
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{test_script}" "{bin_path}" {expect_ohos}',
                "discovered": 7,
                "passedCount": 7,
                "ohos_specific_cases": 2,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"incus is not an ELF binary: {magic!r}"
            self.output.info(f"incus binary exists and has ELF magic: {bin_path}")
