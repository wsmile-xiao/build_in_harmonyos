#!/usr/bin/env python3
"""test_package for eta 1.0.1 — runs the installed `eta` binary like a user."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class EtaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly;
        # wrap the consumer script with the device bash like other packages.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
