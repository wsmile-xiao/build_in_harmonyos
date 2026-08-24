#!/usr/bin/env python3
"""Conan test_package — automysqlbackup 2.6-debian.4.

验证 automysqlbackup 可执行 + 实际运行（R34：实质调用被测包——
bash -n 语法解析 + 运行输出）。
调用 test_automysqlbackup.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class AutomysqlbackupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(
            self.dependencies["automysqlbackup"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_automysqlbackup.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
