#!/usr/bin/env python3
"""Conan test_package — kernel-modules 0.1.7（数据/配置资源包 R34 真实校验）。

L1 官方测试：运行 test_kernel_modules.py —— 真实校验打包产物：
  1. share/kernel-modules-hook/ 下 4 个制品文件存在且非空；
  2. licenses/UNLICENSE 存在且非空；
  3. 从两个 hook 提取 Exec 内嵌 shell 命令 → sh -n 校验语法（真实执行）；
  4. 从 service 提取 ExecStart 内嵌 bash 命令 → bash -n 校验语法（bash 可用时）。
对被测包真实依赖（self.requires(self.tested_reference_str)），非 print-only/
pass-only 空壳（PF3/R34）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class KernelModulesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["kernel-modules"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_kernel_modules.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
