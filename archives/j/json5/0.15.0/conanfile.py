#!/usr/bin/env python3
"""Conan recipe for json5 — 纯 Python JSON5 解析库（无 C 扩展、零依赖）。

json5 是纯 Python 库（pyproject/setuptools 构建，无编译）。注意：本环境
conan create 对 python-require 型配方会静默跳过构建（实测 EXIT=0 无产物）
——故用 application 型（dataproperty/pytablewriter 先例），需配套
commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class Json5Conan(ConanFile):
    name = "json5"
    version = "0.15.0"
    package_type = "application"
    license = "Apache-2.0"
    homepage = "https://github.com/dpranke/pyjson5"
    description = "json5 — JSON5 data-interchange format parser (pure Python)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/json5-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "tests", "docs", "Makefile", "MANIFEST*", "sample.json5",
                ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/json5-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src_pkg = os.path.join(staging, "json5")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"json5 package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "json5"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
