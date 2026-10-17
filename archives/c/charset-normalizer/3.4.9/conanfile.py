#!/usr/bin/env python3
"""Conan recipe for charset-normalizer — 纯 Python 字符编码检测库（零依赖）。

charset-normalizer 是纯 Python 库（pyproject 构建，无编译），src/ 布局，
包在 src/charset_normalizer（含 data/ 编码数据）。注意：本环境 conan
create 对 python-require 型配方会静默跳过构建（实测 EXIT=0 无产物）
——故用 application 型（dataproperty/pytablewriter 先例），需配套
commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class CharsetNormalizerConan(ConanFile):
    name = "charset-normalizer"
    version = "3.4.9"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/Ousret/charset_normalizer"
    description = "charset-normalizer — The Real First Universal Charset Detector (pure Python)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/charset-normalizer-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "tests", "docs", "data", "dev-requirements.txt",
                "noxfile.py", "SECURITY.md", "CHANGELOG.md", "_mypyc_hook",
                ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/charset-normalizer-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # src/ 布局：包在 src/charset_normalizer
        src_pkg = os.path.join(staging, "src", "charset_normalizer")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"charset_normalizer package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "charset_normalizer"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
