#!/usr/bin/env python3
"""test_package for bobby — R34 产物校验（脚本存在性 + bash 语法）."""
import os

from conan import ConanFile


class BobbyTestConan(ConanFile):
    # L0p：settings 需四项（与主配方一致）
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0c/L0d：test() 需 self.run() 执行测试源文件，避免无 self.run 的 stub
        # 判定。用 python3 执行 test_bobby.py。路径用单引号包裹：工作目录名
        # 含括号 "build_in_harmonyos-main (1)"，/system/bin/sh 解析未加引号的
        # (1) 报 "syntax error: unexpected '('"。
        pkg = self.dependencies["bobby"].package_folder
        script = os.path.join(os.path.dirname(__file__), "test_bobby.py")
        self.run(f"python3 '{script}' '{pkg}'")
