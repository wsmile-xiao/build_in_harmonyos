#!/usr/bin/env python3
"""Conan recipe for pytz — 纯 Python 时区库（零依赖，含 zoneinfo 数据）。

pytz 是纯 Python 库（setuptools 构建，无编译），顶层 pytz/ 包内含 604 个
zoneinfo 时区数据文件。注意：本环境 conan create 对 python-require 型配方
会静默跳过构建（实测 EXIT=0 无产物）——故用 application 型（dataproperty/
pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class PytzConan(ConanFile):
    name = "pytz"
    version = "2026.3.post1"
    package_type = "application"
    license = "MIT"
    homepage = "https://pythonhosted.org/pytz/"
    description = "pytz — World timezone definitions, modern and historical (pure Python)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/pytz-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "tests", "docs", "Makefile", "MANIFEST*",
                ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/pytz-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src_pkg = os.path.join(staging, "pytz")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"pytz package missing: {src_pkg}")
        # 顶层 pytz/ 包（含 zoneinfo 数据目录）
        shutil.copytree(
            src_pkg, os.path.join(site, "pytz"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
