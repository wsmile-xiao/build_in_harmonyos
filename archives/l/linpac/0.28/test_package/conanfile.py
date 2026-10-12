#!/usr/bin/env python3
"""Conan test_package for linpac 0.28 (AX.25 packet radio terminal).

linpac is a CLI/terminal application, so the L1 test drives the installed
binary for real (R34) and asserts the OHOS behaviour that the recipe patches
in: the terminal starts up and its per-user lock file is created in a writable
runtime directory, because OpenHarmony has no /var/lock.
"""
import os

from conan import ConanFile


class LinpacTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
