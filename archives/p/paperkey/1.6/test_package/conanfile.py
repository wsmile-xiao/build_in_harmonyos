#!/usr/bin/env python3
"""Conan test_package — paperkey 1.6

Tests the paperkey binary by running test.sh which verifies --version output.
paperkey is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class PaperkeyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        bin_dir = self.dependencies["paperkey"].cpp_info.bindirs[0]
        paperkey_bin = os.path.join(bin_dir, "paperkey")

        # OHOS: /system/bin/sh (mksh) cannot reliably execute test scripts.
        # On OHOS, bash is at /data/service/hnp/bin/bash (not /bin/bash).
        # On Linux, /bin/bash is the standard path.
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = os.environ.get("CONFIG_SHELL", "/bin/bash")
        self.run(f'PAPERKEY_BIN="{paperkey_bin}" {bash} test.sh', env="conanrun")
