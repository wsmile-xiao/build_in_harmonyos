#!/usr/bin/env python3
"""Test package for cronic 3.

Runs the installed `cronic` script against the three documented scenarios
(generic, test_cronic.sh) plus the HarmonyOS-specific runtime constraints
(test_cronic_ohos.sh): shebang/no /bin/bash, HMDFS exec-bit independence,
writable-TMPDIR requirement, UTF-8 payloads and HNP bash compatibility.

The script is invoked explicitly as `bash <pkg>/bin/cronic`, because on
HarmonyOS there is no /bin/bash (bash lives in /data/service/hnp/bin and is
on PATH) and HMDFS exec bits are unreliable, so the shebang cannot be
trusted. The functional logic lives in the shell scripts so this recipe stays
a thin driver (no inline echo/print).
"""

import os

from conan import ConanFile


class CronicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["cronic"].package_folder
        cronic_bin = os.path.join(pkg_folder, "bin", "cronic")
        test_script = os.path.join(self.recipe_folder, "test_cronic.sh")
        self.run(f'bash "{test_script}" "{cronic_bin}"')
        ohos_script = os.path.join(self.recipe_folder, "test_cronic_ohos.sh")
        self.run(f'bash "{ohos_script}" "{cronic_bin}"')
