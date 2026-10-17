#!/usr/bin/env python3
"""Conan test_package for typedload 2.41 — consumer check (OHOS aarch64).

运行 test_typedload.py（真实测试源文件，满足 L0c）——它直接 import
conan 包内落地的 `typedload`，覆盖打包契约、上游核心 API 与 3 项
**鸿蒙（OHOS）专有断言**。

PYTHONPATH 显式注入（aiohttp 教训：package_info 里 print PYTHONPATH
并不会自动传播到测试进程）。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class TypedloadTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        ref = self.dependencies["typedload"].ref
        if str(ref.version) != "2.41":
            raise ConanException(f"unexpected tested version: {ref}")

        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        pkg = self.dependencies["typedload"].package_folder
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "typedload")):
            raise ConanException(f"typedload package missing under {site}")
        os.environ["PYTHONPATH"] = site
        # 消费者进程 import 包内模块时不得把 __pycache__/*.pyc 写回包目录
        # （会改动已打包内容，也会让「payload 是纯 Python 源码」的断言失真）
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

        test_script = os.path.join(os.path.dirname(__file__), "test_typedload.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_typedload.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
