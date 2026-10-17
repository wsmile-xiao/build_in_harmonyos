#!/usr/bin/env python3
"""Conan recipe for pytablewriter — Python 表格输出库（纯 Python，无 C 扩展）。

pytablewriter 是纯 Python 库（setuptools 构建，无编译），无 CLI 入口。
注意：此环境 conan create 对 python-require 型配方会静默跳过构建（实测
EXIT=0 无产物）——故用 application 型（dataproperty 先例），需配套
commands.json（R38）。
依赖链（requirements.txt 核验）：DataProperty、mbstrdecoder、pathvalidate、
tabledata、tcolorpy、typepy —— 均已发布 ohpcd。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class PytablewriterConan(ConanFile):
    name = "pytablewriter"
    version = "1.2.1"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/thombashi/pytablewriter"
    description = ("pytablewriter — Python library to write tables in various "
                   "formats (pure Python)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # 上游 requirements.txt 核验：DataProperty/mbstrdecoder/pathvalidate/
    # tabledata/tcolorpy/typepy 为运行时必需（均已在 ohpcd）
    requires = (
        "dataproperty/1.1.1",
        "mbstrdecoder/1.1.5",
        "pathvalidate/3.3.1",
        "tabledata/1.3.5",
        "tcolorpy/0.1.7",
        "typepy/2.0.0",
    )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （源外目录——纯 Python）——参考 typepy 同款方案
        staging = "/data/storage/el2/base/cache/pytablewriter-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "docs", "Makefile", "MANIFEST*", "ss", "examples",
                ".github", ".gitignore", ".readthedocs.yaml",
                "CHANGELOG.md", "tox.ini", "requirements"))

    def package(self):
        staging = "/data/storage/el2/base/cache/pytablewriter-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # pytablewriter 顶层普通 layout（sdist 顶层 pytablewriter/）——
        # 复制 pytablewriter/ 到 site-packages
        src_pkg = os.path.join(staging, "pytablewriter")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"pytablewriter package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "pytablewriter"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
