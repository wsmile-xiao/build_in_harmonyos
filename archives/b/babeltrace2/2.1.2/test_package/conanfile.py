#!/usr/bin/env python3
"""test_package for babeltrace2 2.1.2 — babeltrace2 二进制冒烟（R34）。"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class Babeltrace2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip run")
            return
        bin_dir = self.dependencies["babeltrace2"].package_folder
        bt = os.path.join(bin_dir, "bin", "babeltrace2")
        self.run(f"{bt} --version", env="conanrun")
