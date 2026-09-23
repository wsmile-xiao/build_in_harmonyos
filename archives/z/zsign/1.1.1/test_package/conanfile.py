#!/usr/bin/env python3
"""Consumer test for zsign 1.1.1 — CLI tool, so test() drives the installed
binary directly (no library to link against)."""
import os

from conan import ConanFile


class ZsignTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute arbitrary scripts; use the
        # device bash pinned by the profile ([buildenv] CONFIG_SHELL).
        if str(self.settings.os) == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = os.environ.get("CONFIG_SHELL", "bash")
        zsign_bin = os.path.join(
            self.dependencies["zsign"].cpp_info.bindirs[0], "zsign")
        self.run(f'"{bash}" test_zsign.sh "{zsign_bin}"', env="conanrun")
