#!/usr/bin/env python3
"""Conan test_package for boa 0.94.14rc21 — 消费测试验证 boa 可执行 + usage。

用法: python3 test_boa.py <package_folder>
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import copy


class BoaTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 把测试脚本复制到构建目录后用 python3 执行（与 bash-unit 等
        # L0d 门禁同款结构——真实执行非 stub）
        copy(self, "test_boa.py", src=self.recipe_folder,
             dst=os.path.join(self.build_folder, "test_package"))
        pkg_folder = self.dependencies["boa"].package_folder
        self.run('python3 test_package/test_boa.py "%s"' % pkg_folder,
                 env="conanrun")
