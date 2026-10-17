#!/usr/bin/env python3
"""Conan test_package for gir-to-d 0.23.3 — consumer check (R34 真实调用).

用 test_girtod.py 把真实的最小 GObject-Introspection 输入喂给打包出来的
girtod，校验它确实生成了预期的 D 绑定源码。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class GirToDTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["gir-to-d"].package_folder
        if not pkg:
            raise ConanException("gir-to-d package_folder is not available")

        binary = os.path.join(pkg, "bin", "girtod")
        if not os.path.isfile(binary):
            raise ConanException(f"packaged binary missing: {binary}")

        test_script = os.path.join(os.path.dirname(__file__), "test_girtod.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_girtod.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
