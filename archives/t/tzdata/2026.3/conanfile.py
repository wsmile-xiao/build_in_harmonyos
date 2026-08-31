#!/usr/bin/env python3
"""Conan recipe for tzdata — IANA 时区数据包（纯 Python 数据包，零依赖）。

tzdata 是 Python 时区数据包（pyproject 构建，无编译），src/ 布局，包在
src/tzdata（__init__.py + zoneinfo 625 数据文件 + zones）。注意：本环境
conan create 对 python-require 型配方会静默跳过构建（实测 EXIT=0 无产物）
——故用 application 型（dataproperty/pytablewriter 先例），需配套
commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class TzdataConan(ConanFile):
    name = "tzdata"
    version = "2026.3"
    package_type = "application"
    license = "Apache-2.0"
    homepage = "https://github.com/python/tzdata"
    description = "tzdata — IANA time zone database packaged for Python (data package)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/tzdata-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "tests", "docs", "Makefile", "MANIFEST*", "NEWS.md",
                "VERSION", "templates", "licenses", "tag_release.sh",
                "tox.ini", ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/tzdata-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # src/ 布局：包在 src/tzdata（含 zoneinfo + zones 数据）
        src_pkg = os.path.join(staging, "src", "tzdata")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"tzdata package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "tzdata"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
