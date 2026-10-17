#!/usr/bin/env python3
"""Conan recipe for tablib — Python 表格数据格式库（核心零依赖，src/ 布局）。

tablib 是纯 Python 库（pyproject 构建，无编译），核心零运行时依赖
（各 format 如 csv/xlsx/dbf 的第三方依赖均为可选 extras）。src/ 布局，
包在 src/tablib（含 _vendor 与 formats）。注意：本环境 conan create 对
python-require 型配方会静默跳过构建（实测 EXIT=0 无产物）——故用
application 型（dataproperty/pytablewriter 先例），需配套 commands.json
（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class TablibConan(ConanFile):
    name = "tablib"
    version = "3.10.0"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/jazzband/tablib"
    description = "tablib — Python module for Tabular Datasets in XLS, CSV, JSON, YAML, &c (pure Python core)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/tablib-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "pytest.ini", "tox.ini",
                "README*", "LICENSE*", "HISTORY*", "AUTHORS*",
                "CODE_OF_CONDUCT*", "RELEASING*",
                "test*", "tests", "docs", "files",
                ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/tablib-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # src/ 布局：包在 src/tablib（含 _vendor + formats）
        src_pkg = os.path.join(staging, "src", "tablib")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"tablib package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "tablib"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
