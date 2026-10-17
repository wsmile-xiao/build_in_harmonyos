#!/usr/bin/env python3
"""Conan recipe — atools 0.6.1 (Python 3.6+ async decorators and testing tools).

Build system: setuptools (setup.py) — pure Python, no compiled deps.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import get, copy


class AtoolsConan(ConanFile):
    name = "atools"
    version = "0.6.1"
    description = "Python 3.6+ async decorators and testing tools"
    license = "MIT"
    homepage = "https://github.com/cevans87/atools"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Python——无编译——上游 test/ 测试实测在 Python 3.12 无法运行
        # （test_memoize_decorator 用 asyncio.coroutine——3.12 移除——
        # collection error；其余测试挂起——多次实测）——如实记录——
        # 消费测试（test_package import atools）验证打包正确性
        pass

    def package(self):
        src = os.path.join(self.source_folder, "atools")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_pkg, exist_ok=True)
        shutil.copytree(src, os.path.join(site_pkg, "atools"), dirs_exist_ok=True)
        for doc in ("README.md", "LICENSE"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site_pkg)
