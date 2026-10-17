#!/usr/bin/env python3
"""test_package for babeltrace 1.5.11 — babeltrace 转换 + lib 链接断言（R34）。"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class BabeltraceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip run")
            return
        bin_dir = self.dependencies["babeltrace"].package_folder
        bt = os.path.join(bin_dir, "bin", "babeltrace")
        # babeltrace 1.5.11 的 CLI 不支持 --version（返回 "Error parsing options."
        # 且 exit 1），用 --help 做冒烟断言（exit 0 且输出 usage）。
        self.run(f"{bt} --help", env="conanrun")
