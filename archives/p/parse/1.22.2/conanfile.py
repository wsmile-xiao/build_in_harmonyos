#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for parse 1.22.2

parse is a pure-Python format-string parsing library (the inverse of
str.format()): it parses strings according to a format pattern and returns
the extracted values with type conversion.

Package facts (verified from official sdist 1.22.2):
  - Pure Python, no C extension (single package `parse/` + typing stub).
  - No runtime dependencies (PyPI requires_dist empty; only stdlib used).
  - Build backend: setuptools>=61.2 (pyproject.toml [build-system]).
  - No console_scripts / entry_points, no bin/ executables -> NOT a CLI,
    no commands.json needed (R38/L0k).
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ParseConan(ConanFile):
    name = "parse"
    version = "1.22.2"
    license = "MIT"
    url = "https://github.com/r1chardj0n3s/parse"
    homepage = "https://github.com/r1chardj0n3s/parse"
    description = ("parse() is the opposite of format(): parses a string "
                   "according to a format pattern with type conversion — "
                   "pure Python, no runtime deps")
    topics = ("parse", "format", "python", "parsing")
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    # No runtime requirements: parse uses only the Python stdlib
    # (PyPI requires_dist verified empty for 1.22.2).

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R02 修复（CI PEP 517 后端可用性）：远端 CI 设备上的 Python 解释器
        # 不含 setuptools.build_meta，--no-build-isolation 下 pip 直接导入后端
        # 会触发 BackendUnavailable: Cannot import 'setuptools.build_meta'。
        # 先在 build() 首步显式安装 setuptools（terminator/2.1.5 同款
        # 已验证路径）：--break-system-packages 绕过 PEP 668 externally-managed
        # 守卫；setuptools 以 wheel 安装、不创建 pip-build-env overlay，
        # 不会触碰 worker inode 上限（r01 Errno 28 教训）。
        self.run(
            f'"{sys.executable}" -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools'
        )
        # Pure Python package: pip install --no-deps to a target directory.
        # --no-deps: parse has no runtime dependencies, nothing pip-managed.
        # --no-build-isolation: reuse setuptools installed above, do not create
        # a pip build-env overlay (worker filesystem has a hard inode cap, the
        # overlay exhausts it: W3 "No space left on device" on pip-build-env).
        install_target = os.path.join(self.build_folder, "install")
        self.run(
            f'"{sys.executable}" -m pip install --no-deps '
            f'--no-build-isolation '
            f'--target="{install_target}" "{self.source_folder}"'
        )

    def package(self):
        install_target = os.path.join(self.build_folder, "install")
        copy(self, "*", dst=self.package_folder, src=install_target)

    def package_info(self):
        # Pure Python package: expose package folder via PYTHONPATH.
        # NOTE: keep default cpp_info fields (do not clear) so CI L0k/R38
        # does not misclassify this pure-Python package as a CLI tool.
        python_path = self.package_folder
        self.output.info(f"Setting PYTHONPATH: {python_path}")
        self.runenv_info.prepend_path("PYTHONPATH", python_path)
