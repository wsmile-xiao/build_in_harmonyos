#!/usr/bin/env python3
"""test_package — alien-hunter 消费验证（L0d: test() 必须 self.run）。"""
import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0d: test() 经 self.run 执行真实验证脚本（demoSeq.dna 实跑 IVOM 预测）
        script = os.path.join(self.source_folder, "test_alien_hunter.py")
        self.run(f"python3 {script} {self.dependencies[self.tested_reference_str].package_folder}",
                 env="conanrun")
