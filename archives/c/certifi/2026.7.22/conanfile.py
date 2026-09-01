#!/usr/bin/env python3
"""Conan recipe for certifi — Python CA 证书包（纯数据+逻辑，零依赖）。

certifi 提供 Mozilla CA 证书 bundle（cacert.pem），纯 Python（无编译）。
注意：本环境 conan create 对 python-require 型配方会静默跳过构建
（实测 EXIT=0 无产物）——故用 application 型（dataproperty/pytablewriter
先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class CertifiConan(ConanFile):
    name = "certifi"
    version = "2026.7.22"
    package_type = "application"
    license = "MPL-2.0"
    homepage = "https://github.com/certifi/python-certifi"
    description = "certifi — Python package for providing Mozilla's CA Bundle (pure Python data)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/certifi-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "tests", "docs", "Makefile", "MANIFEST*",
                ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/certifi-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src_pkg = os.path.join(staging, "certifi")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"certifi package missing: {src_pkg}")
        # certifi/ 含 __init__.py + cacert.pem 数据（证书 bundle 需一并拷入）
        shutil.copytree(
            src_pkg, os.path.join(site, "certifi"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
