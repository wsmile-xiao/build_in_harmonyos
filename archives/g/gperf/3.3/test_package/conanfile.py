#!/usr/bin/env python3
"""Conan test_package for gperf 3.3.

gperf 是**构建工具**（只装 bin/gperf），测试方式为**真实执行 + 真实生成**：
  - gperf --version  断言版本号
  - 用一个真实 .gperf 输入，让 gperf 生成 C 查找代码，再断言生成物含预期符号
    （直接证明它具备 eudev 所需的「由关键字表生成查找表」能力，而非仅打印版本号）

实际断言由 test_gperf.sh 承担（L0c 真实测试源文件）。
"""
import os

from conan import ConanFile


class GperfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_gperf.sh")
        # env="conanrun"：gperf 为动态链接可执行文件（若为 shared 构建），
        # 运行时需 LD_LIBRARY_PATH 含依赖 lib 目录。
        self.run(f"sh '{script}' '{pkg}'", env="conanrun")
