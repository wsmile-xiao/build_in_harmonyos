#!/usr/bin/env python3
"""Conan recipe for webencodings — 纯 Python WHATWG 编码字符集解析库（零依赖）。

webencodings 是纯 Python 库（pyproject 构建，无编译），顶层 webencodings/
包（3 个 .py）。注意：本环境 conan create 对 python-require 型配方会静默
跳过构建（实测 EXIT=0 无产物）——故用 application 型（dataproperty/
pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class WebencodingsConan(ConanFile):
    name = "webencodings"
    version = "0.6.1"
    package_type = "application"
    license = "BSD-3-Clause"
    homepage = "https://github.com/SimonSapin/python-webencodings"
    description = "webencodings — Character encoding aliases for legacy web content (pure Python)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/webencodings-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "tests", "docs", "Makefile", "MANIFEST*", "mklabels.py",
                ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/webencodings-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src_pkg = os.path.join(staging, "webencodings")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"webencodings package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "webencodings"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
