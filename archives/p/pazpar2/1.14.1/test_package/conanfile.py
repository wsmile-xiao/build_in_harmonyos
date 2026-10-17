#!/usr/bin/env python3
"""test_package — pazpar2 1.14.1 (HarmonyOS PC): drive the installed daemon."""
import os
import shutil

from conan import ConanFile


class Pazpar2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap the
        # driver in bash; python3 resolves through the inherited PATH.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        python = shutil.which("python3") or "python3"
        self.run(f'{bash} -c "{python} -u test_pazpar2.py"', env="conanrun")
