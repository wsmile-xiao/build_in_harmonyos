#!/usr/bin/env python3
"""Conan consumer test for wagyu 0.6.1 (Rust binary package).

Layered verification (see test_wagyu.py for the per-assertion breakdown):
  1. package integrity — packaged `bin/wagyu` exists;
  2. consumer smoke + real wallet generation (A1–A8) — exercises the entropy
     path that the recipe's getrandom registry patch re-enables on OHOS;
  3. HarmonyOS trait assertions (B1–B4) — AArch64 / musl loader / code
     signature / non-empty executable.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class WagyuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_wagyu.py"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # test_type = "explicit"：必须显式声明被测包，否则图计算直接报
        # "doesn't declare any requirement, use self.tested_reference_str"
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["wagyu"].package_folder
        exe = os.path.join(package_folder, "bin", "wagyu")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing wagyu executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_wagyu.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(
                f"wagyu test_package failed with exit code {result}")
