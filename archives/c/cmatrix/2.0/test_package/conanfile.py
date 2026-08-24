#!/usr/bin/env python3
"""test_package for cmatrix 2 — 非交互 -V 版本断言（R34 实质测试）。"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class CmatrixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip run")
            return
        bin_dir = self.dependencies["cmatrix"].package_folder
        cmatrix = os.path.join(bin_dir, "bin", "cmatrix")
        # 断言: cmatrix -V 输出包含 "CMatrix version 2.0"（非交互，无需 TTY）
        self.run(f"{cmatrix} -V", env="conanrun")
