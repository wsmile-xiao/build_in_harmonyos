#!/usr/bin/env python3
"""Conan recipe for zope.interface 8.6 (pure-Python packaging).

zope.interface is a setuptools-built Python package with an *optional* C
extension (_zope_interface_coptimizations.c).  setup.py's optional_build_ext
lets the C build fail and falls back to pure Python, which is functionally
complete (upstream runs its "pure" CI job with PURE_PYTHON=1).

This repo's CI has limited support for cross-compiling Python C extensions,
so the package is shipped as pure Python (same as python-dateutil/six
precedents): the package source is copied to lib/python3.12/site-packages.

Runtime dependencies (PyPI requires_dist, verified): none.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)


class ZopeInterfaceConan(ConanFile):
    name = "zope.interface"
    version = "8.6"
    package_type = "python-require"
    license = "ZPL-2.1"
    homepage = "https://github.com/zope/zope.interface"
    description = ("Interfaces for Python — lazr.config dependency chain "
                   "bottom layer (pure Python packaging; C optimizations "
                   "are optional acceleration and are skipped)")
    settings = "os", "arch", "compiler", "build_type"
    # PyPI requires_dist 核验：zope.interface 8.6 无运行时依赖
    # （仅 docs/test extras：Sphinx、zope.event、zope.testing、coverage）

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["zope.interface"],
            strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # 本包无补丁——no-op
        # pip/setuptools 元数据构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/zope-interface-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "tox.ini", "README*", "CHANGES*",
                "COPYRIGHT*", "LICENSE*", "MANIFEST*", "PKG-INFO",
                "buildout.cfg", "build.cmd", "benchmarks", "docs",
                ".git", ".github", ".manylinux*",
                ".pre-commit-config.yaml", ".readthedocs.yaml",
                ".edit-tracker.json", "test*", "tests"))

    def package(self):
        staging = "/data/storage/el2/base/cache/zope-interface-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # zope 是 PEP 420 namespace 包（src/zope/ 无 __init__.py）——整体
        # 复制 src/zope（含 zope/interface 包），排除 tests/ 与 C 源码
        src_zope = os.path.join(staging, "src", "zope")
        if not os.path.isdir(src_zope):
            raise ConanException(f"zope package missing: {src_zope}")
        shutil.copytree(
            src_zope, os.path.join(site, "zope"),
            ignore=shutil.ignore_patterns(
                "tests", "__pycache__",
                "_zope_interface_coptimizations.c"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
