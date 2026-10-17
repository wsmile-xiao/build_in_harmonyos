#!/usr/bin/env python3
"""Conan test_package for setuptools 84.0.0 — consumer check (R34 真实 API).

以消费者视角使用**已打包**的 setuptools：不仅 import 校验，还真实把它作为
PEP 517 构建后端（setuptools.build_meta）构建一个最小 wheel，并验证
distutils 已被 _distutils_hack 劫持到 setuptools 自带的 _distutils。

env="conanrun" 注入是必需的：包侧 package_info() 用 runenv_info 声明了
PYTHONPATH，裸 subprocess 会丢失该注入。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class SetuptoolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["setuptools"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")

        # 载荷完整性：四要素缺一不可
        for entry in ("setuptools", "_distutils_hack",
                      "distutils-precedence.pth"):
            if not os.path.exists(os.path.join(site, entry)):
                raise ConanException(
                    f"setuptools payload incomplete, missing: {site}/{entry}")
        dist_infos = [d for d in os.listdir(site)
                      if d.startswith("setuptools-")
                      and (d.endswith(".dist-info") or d.endswith(".egg-info"))]
        if not dist_infos:
            raise ConanException(
                f"setuptools-*.dist-info / *.egg-info missing under {site} "
                "(version resolution would break)")

        script = os.path.join(os.path.dirname(__file__), "test_setuptools.py")
        if not os.path.isfile(script):
            raise ConanException(f"test_setuptools.py missing: {script}")

        self.run(f'python3 "{script}" "{site}"', env="conanrun")
