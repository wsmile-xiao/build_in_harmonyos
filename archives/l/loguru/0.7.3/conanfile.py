#!/usr/bin/env python3
"""Conan recipe for loguru — 纯 Python 日志库（OHOS 下零依赖）。

loguru 是纯 Python 库（pyproject 构建，无编译）。依赖均为条件性：
colorama/win32-setctime 仅 win32、aiocontextvars 仅 py<3.7——OHOS
(Python 3.12, Linux) 下零运行时依赖。注意：本环境 conan create 对
python-require 型配方会静默跳过构建（实测 EXIT=0 无产物）——故用
application 型（dataproperty/pytablewriter 先例），需配套 commands.json
（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class LoguruConan(ConanFile):
    name = "loguru"
    version = "0.7.3"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/Delgan/loguru"
    description = "loguru — Python logging made (stupidly) simple (pure Python)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/loguru-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "tests", "docs", "Makefile", "MANIFEST*",
                ".git", ".gitignore", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/loguru-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src_pkg = os.path.join(staging, "loguru")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"loguru package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "loguru"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
