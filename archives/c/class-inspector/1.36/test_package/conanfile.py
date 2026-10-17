#!/usr/bin/env python3
"""Conan test_package for class-inspector 1.36 — consumer check (R34 真实 API).

通过 test_class_inspector.py 驱动 perl 加载 <pkg> 中的 Class::Inspector 与
Class::Inspector::Functions 并真实调用其全部公开接口。env="conanrun" 注入
is required（裸 subprocess 会丢失 conanrun 环境注入，参见 perl-uri 先例教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ClassInspectorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["class-inspector"].package_folder
        # 安装前缀随 perl 构建而异 → 遍历定位 Class/Inspector.pm。
        # 模块在 <site>/Class/Inspector.pm，故 site 需上溯一级
        # （不可返回末级目录，否则 -I 指向错误层级）。
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Inspector.pm" in files and os.path.basename(root) == "Class":
                site = os.path.dirname(root)
                break
        if not site:
            raise ConanException("Class/Inspector.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_class_inspector.py")
        if not os.path.isfile(test_script):
            raise ConanException(
                f"test_class_inspector.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
