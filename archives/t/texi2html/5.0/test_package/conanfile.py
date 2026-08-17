#!/usr/bin/env python3
"""test_package — texi2html 消费验证（L0d: test() 必须 self.run）。"""
import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0d: test() 经 self.run 执行真实验证脚本（脚本存在 + perl -c 语法）
        # perl 用依赖制品完整路径（conanrun 未注入 perl/bin 到 PATH）
        script = os.path.join(self.source_folder, "test_texi2html.py")
        perl_pkg = self.dependencies["perl"].package_folder
        self.run(f"python3 {script} "
                 f"{self.dependencies[self.tested_reference_str].package_folder} "
                 f"{perl_pkg}", env="conanrun")
