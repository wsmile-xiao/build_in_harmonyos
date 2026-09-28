#!/usr/bin/env python3
"""Conan consumer test for the Yavta command-line package."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class YavtaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping execution test: target OHOS binary cannot run on the build host")
            return
        # OHOS /system/bin/sh cannot reliably execute ELF binaries; use HNP bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
