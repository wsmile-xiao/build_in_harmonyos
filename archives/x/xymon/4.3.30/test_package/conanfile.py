#!/usr/bin/env python3
"""test_package for xymon — consumer verification of the HarmonyOS PC port.

Runs `test.sh`, which invokes the installed xymon binaries the way a real user
would and additionally performs an OHOS-specific end-to-end execution.
"""
import os

from conan import ConanFile


class XymonTestConan(ConanFile):
    """Executable package: drive the installed binaries through test.sh."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so the script
        # is driven with an explicit bash.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} test.sh", env="conanrun")
