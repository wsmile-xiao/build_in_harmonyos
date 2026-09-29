#!/usr/bin/env python3
"""test_package — robodoc 4.99.44 (autotools executable).

Runs two shell suites against the packaged binaries:
  * test.sh                — consumer smoke test (--version / usage)
  * ohos_specific_test.sh  — HarmonyOS-specific adaptation test
                             (native OHOS AArch64 ELF, config triplet,
                              real documentation extraction on HMDFS)
"""
import os

from conan import ConanFile


class RobodocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot reliably execute ELF binaries;
        # wrap execution with bash as the other recipes in this repository do.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
        self.run(f"{bash} ohos_specific_test.sh", env="conanrun")
