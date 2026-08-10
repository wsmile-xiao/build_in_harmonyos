#!/usr/bin/env python3
"""test_package for alpine-make-vm-image executable — runs the script to verify."""
import os

from conan import ConanFile


class AlpineMakeVmImageTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute some binaries.
        # Use bash to wrap execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
