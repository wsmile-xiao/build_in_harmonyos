#!/usr/bin/env python3
"""Conan recipe for html5lib — 纯 Python HTML5 解析库。

html5lib 是符合 WHATWG HTML 规范的纯 Python HTML 解析库（pyproject 构建，
无编译），顶层 html5lib/ 包（大量 .py 模块）。依赖 six>=1.9（已发布
six/1.17.0）+ webencodings（已发布 webencodings/0.6.1）。
注意：本环境 conan create 对 python-require 型配方会静默跳过构建
（实测 EXIT=0 无产物）——故用 application 型（webencodings/dataproperty/
pytablewriter 先例），需配套 commands.json（R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class Html5libConan(ConanFile):
    name = "html5lib"
    version = "1.1"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/html5lib/html5lib-python"
    description = "html5lib — HTML parser based on the WHATWG HTML specification (pure Python)"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # 纯 Python 运行时依赖（已发布 six/1.17.0 + webencodings/0.6.1）
        self.requires("six/1.17.0")
        self.requires("webencodings/0.6.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无源码补丁（apply_conandata_patches 为空操作）
        apply_conandata_patches(self)
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging（源外目录）
        staging = "/data/storage/el2/base/cache/html5lib-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "tox.ini", "pytest.ini",
                "README*", "LICENSE*", "CHANGES*", "AUTHORS*",
                "PKG-INFO", "MANIFEST*", "requirements*",
                "test*", "tests", "docs", ".git", ".gitignore",
                ".github", ".pytest.expect"))

    def package(self):
        staging = "/data/storage/el2/base/cache/html5lib-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src_pkg = os.path.join(staging, "html5lib")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"html5lib package missing in staging: {src_pkg}")
        shutil.copytree(src_pkg, os.path.join(site, "html5lib"),
                        dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
