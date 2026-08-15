#!/usr/bin/env python3
"""Conan test_package — genext2fs 1.5.0.

验证 genext2fs 可执行并完成实际 ext2 镜像生成（R34：实质调用被测包）。
调用 test_genext2fs.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class Genext2fsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["genext2fs"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_genext2fs.sh")
        # 传入 build_folder 作为可写临时目录（/tmp 在部分沙箱只读）
        self.run(f'sh "{script}" "{bin_dir}" "{self.build_folder}"')
