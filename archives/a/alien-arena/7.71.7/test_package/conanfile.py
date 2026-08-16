#!/usr/bin/env python3
"""test_package — alien-arena 消费验证（L0d: test() 必须 self.run）。"""
import os
from conan import ConanFile
from conan.tools.files import save


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0d: test() 经 self.run 执行真实验证脚本（ELF 检查）
        script = os.path.join(self.source_folder, "test_alien_arena.py")
        self.run(f"python3 {script} {self.dependencies[self.tested_reference_str].package_folder}",
                 env="conanrun")
