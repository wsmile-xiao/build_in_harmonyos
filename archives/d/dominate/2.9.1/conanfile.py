#!/usr/bin/env python3
"""Conan recipe for dominate — 纯 Python DOM/HTML 生成库（零依赖）。

dominate 是纯 Python 库（pyproject 构建，无编译），顶层 dominate/ 包
（8 个 .py）。注意：本环境 conan create 对 python-require 型配方会静默
跳过构建（实测 EXIT=0 无产物）——故用 application 型（dataproperty/
pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class DominateConan(ConanFile):
    name = "dominate"
    version = "2.9.1"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/Knio/dominate"
    description = "dominate — Python library for creating and manipulating HTML documents (pure Python)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/dominate-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "tests", "setup", "docs", "Makefile", "MANIFEST*",
                ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/dominate-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src_pkg = os.path.join(staging, "dominate")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"dominate package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "dominate"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
