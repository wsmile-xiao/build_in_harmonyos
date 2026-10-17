#!/usr/bin/env python3
"""Consumer test for qla-tools 20140529.

Runs test.sh in the conanrun environment. test.sh executes ALL four installed
upstream scripts (no sample left untested) and asserts their observable
behaviour on OHOS, including three HarmonyOS-specific checks (shebang
resolvability, read-only /tmp, HarmonyOS kernel release string).
"""
import os

from conan import ConanFile


class QlaToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) is not guaranteed to run these scripts;
        # invoke test.sh through the OHOS bash explicitly.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
