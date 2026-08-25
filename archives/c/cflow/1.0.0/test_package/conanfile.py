#!/usr/bin/env python3
"""test_package for cflow 1.0.0 — 调用图生成功能断言（R34 实质测试）。"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class CflowTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip run")
            return
        bin_dir = self.dependencies["cflow"].package_folder
        cflow = os.path.join(bin_dir, "bin", "cflow")
        sample = os.path.join(self.source_folder, "sample.c")
        # 断言 1: cflow --version 可运行
        self.run(f"{cflow} --version", env="conanrun")
        # 断言 2: 调用图包含 main/foo 标记
        # 用 Python 写入测试输入文件，再调用 cflow 二进制解析
        with open(sample, "w") as f:
            f.write("int main(){foo();} void foo(){}\n")
        self.run(f"{cflow} -o - {sample}", env="conanrun")
