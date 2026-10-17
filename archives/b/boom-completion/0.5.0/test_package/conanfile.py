#!/usr/bin/env python3
"""test_package for boom-completion — R34 产物校验.

纯脚本包（无库/头文件），test() 直接检查包内补全脚本存在 + 内容关键函数。
"""
import os

from conan import ConanFile


class BoomCompletionTestConan(ConanFile):
    # L0p：settings 需四项（与主配方一致）
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0c/L0d：test() 需 self.run() 执行测试源文件，避免无 self.run 的 stub
        # 判定。用 python3 执行 test_boom_completion.py。路径用单引号包裹：
        # 工作目录名含括号 "build_in_harmonyos-main (1)"，/system/bin/sh 解析
        # 未加引号的 (1) 报 "syntax error: unexpected '('"。
        pkg = self.dependencies["boom-completion"].package_folder
        script = os.path.join(os.path.dirname(__file__), "test_boom_completion.py")
        self.run(f"python3 '{script}' '{pkg}'")
