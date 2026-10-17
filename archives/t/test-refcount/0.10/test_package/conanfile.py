#!/usr/bin/env python3
"""Conan test_package for test-refcount 0.10 — consumer check (R34 真实 API).

通过 test_test_refcount.py 驱动 perl 加载 <pkg> 中的 Test::Refcount 并真实调用
其 API。env="conanrun" 注入 is required（裸 subprocess 会丢失 conanrun 环境注入，
参见 perl-uri 先例的 FileNotFoundError 教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class TestRefcountTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["test-refcount"].package_folder
        # 安装前缀随 perl 构建而异 → 遍历定位 Test/Refcount.pm。
        # 模块在 <site>/Test/Refcount.pm，故 site = "Test" 目录的父级
        # （不可返回 Test/ 本身，否则 -I 指向错误层级）。
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Refcount.pm" in files and os.path.basename(root) == "Test":
                site = os.path.dirname(root)
                break
        if not site:
            raise ConanException("Test/Refcount.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__), "test_test_refcount.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_test_refcount.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
