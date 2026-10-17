#!/usr/bin/env python3
"""Conan consumer recipe for Yale 5.0.95 installed-data tests."""

import os
import platform
import shlex

from conan import ConanFile


class YaleTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(os.path.dirname(__file__), "test_data.py")
        ohos_option = " --require-ohos" if platform.system() == "HarmonyOS" else ""
        self.run(
            f"python3 {shlex.quote(test_script)}{ohos_option}",
            env="conanrun",
        )
