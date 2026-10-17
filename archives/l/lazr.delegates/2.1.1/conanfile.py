#!/usr/bin/env python3
"""Conan recipe for lazr.delegates 2.1.1 (pure-Python packaging).

lazr.delegates is a setuptools-built pure-Python package (no C extension,
no compiled artifacts): the whole payload is src/lazr/delegates/ under the
`lazr` namespace package (src/lazr/__init__.py wraps pkg_resources in
try/except and falls back to pkgutil.extend_path — PEP 420 compatible, so
setuptools is NOT a runtime requirement on HarmonyOS and is intentionally
excluded from `requires`; ohpcd does not publish it either).

Packaging follows the chain precedents zope.interface/8.6 and
lazr.delegates/4.0.0 (lazr.config -> lazr.delegates -> zope.interface): the
package source is copied to lib/python3.12/site-packages, so the packaged
artifact is a python-require that downstream lazr.config imports directly.

Runtime dependencies (PyPI requires_dist, verified): only zope.interface
(setuptools is declared by setup.cfg but never imported at runtime; the
docs extra Sphinx is needed only while running the upstream doctests).

Note: lazr.delegates 2.1.1 __init__.py calls
importlib.metadata.version("lazr.delegates") at import time — the
src/lazr.delegates.egg-info metadata must be packaged alongside, otherwise
import fails with PackageNotFoundError.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)


class LazrDelegatesConan(ConanFile):
    name = "lazr.delegates"
    version = "2.1.1"
    package_type = "python-require"
    license = "LGPL-3.0"
    homepage = "https://launchpad.net/lazr.delegates"
    description = ("Decorator helpers that simplify class composition "
                   "(delegate_to / Passthrough) -- lazr.config dependency "
                   "chain middle layer, pure Python packaging")
    settings = "os", "arch", "compiler", "build_type"
    # PyPI requires_dist 核验：lazr.delegates 2.1.1 运行时仅依赖
    # zope.interface（docs extra：Sphinx——仅上游 doctests 需要）
    requires = "zope.interface/8.6"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["lazr.delegates"],
            strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # 本包无补丁——no-op
        # 纯 Python 无编译——copytree 源码到**源外** staging（build 内
        # 递归复制有误提升教训，同 zope.interface/python-dateutil）
        staging = "/data/storage/el2/base/cache/lazr-delegates-stage-2.1.1"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "setup.py", "setup.cfg",
                "pyproject.toml", "tox.ini", "README*", "NEWS*",
                "CONTRIBUTING*", "COPYING*", "LICENSE*", "MANIFEST*",
                "SECURITY*", "docs", "benchmarks",
                ".git", ".github", ".flake8", ".launchpad.yaml",
                ".pre-commit-config.yaml", ".readthedocs.yaml",
                ".woke.yaml", ".edit-tracker.json", ".tarball-sha256",
                "test*", "tests"))

    def package(self):
        staging = "/data/storage/el2/base/cache/lazr-delegates-stage-2.1.1"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # lazr 是 namespace 包（src/lazr/__init__.py 存在，pkg_resources
        # try/except 兜底 pkgutil）——整体复制 src/lazr（含 lazr/delegates），
        # 排除 tests/、__pycache__、docs/
        src_lazr = os.path.join(staging, "src", "lazr")
        if not os.path.isdir(src_lazr):
            raise ConanException(f"lazr package missing: {src_lazr}")
        shutil.copytree(
            src_lazr, os.path.join(site, "lazr"),
            ignore=shutil.ignore_patterns(
                "tests", "__pycache__", "docs"))
        # lazr.delegates 的 __init__.py 在 import 时调用
        # importlib.metadata.version("lazr.delegates")——必须携带
        # egg-info 元数据，否则 PackageNotFoundError 导致 import 失败
        egginfo = os.path.join(staging, "src", "lazr.delegates.egg-info")
        if os.path.isdir(egginfo):
            shutil.copytree(
                egginfo, os.path.join(site, "lazr.delegates.egg-info"),
                ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
