#!/usr/bin/env python3
"""Conan test_package for awk 20251225 — executable smoke test.

Verifies that the awk binary is functional after installation.
Runs test.sh which checks --version, field extraction, gsub, and arrays.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AwkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
            # Use bash to wrap binary execution.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} "{os.path.join(self.source_folder, "test.sh")}"', env="conanrun")
