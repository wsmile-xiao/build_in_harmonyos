#!/usr/bin/env python3
"""test_package — bitcoin 消费验证（L0d: test() 必须 self.run）。"""
import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0d: test() 经 self.run 执行真实验证脚本（ELF + --version 检查）
        script = os.path.join(self.source_folder, "test_bitcoin.py")
        self.run(f"python3 {script} {self.dependencies[self.tested_reference_str].package_folder}",
                 env="conanrun")
