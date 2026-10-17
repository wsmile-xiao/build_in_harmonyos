#!/usr/bin/env python3
"""test_package for shellia — R34 产物校验（ia* 库文件存在 + bash source 验证）."""
import os

from conan import ConanFile


class ShelliaTestConan(ConanFile):
    # L0p：settings 需四项（与主配方一致）
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34/L0c：test() 需 self.run() 执行测试源文件，避免空壳 stub。
        pkg = self.dependencies["shellia"].package_folder
        script = os.path.join(os.path.dirname(__file__), "test_shellia.sh")
        self.run(f"bash '{script}' '{pkg}'")