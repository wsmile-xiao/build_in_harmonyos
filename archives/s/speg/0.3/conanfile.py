#!/usr/bin/env python3
"""Conan recipe — speg 0.3 (avakar/speg, pure-Python PEG parser library).

Pure Python package with no C/C++ sources and no autotools/CMake build
system (PyPI sdist: setup.py + speg/ + egg-info only). No third-party
runtime dependencies. Port follows the s3transfer/0.19.2 pure-Python
precedent: build() is a no-op, package() copies speg/ under lib/python3,
package_info() exposes no libs, and test_package runs a real API consumer
test (R34) that parses a small grammar with speg.peg().
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SpegConan(ConanFile):
    name = "speg"
    version = "0.3"
    package_type = "python-require"
    # 纯 Python 库（无 C/C++、无可执行文件）——package_type 用 python-require，
    # 避免 L0k(R38) 把包当作 CLI 工具要求 commands.json（speg 无 bin/ 产物）。
    # 参考 zipp/aetos 纯 Python 库先例。
    license = "MIT"
    homepage = "https://github.com/avakar/speg"
    description = ("speg — PEG-based parser interpreter with memoization "
                   "(pure Python, no third-party deps)")
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 纯 Python——无编译——安装 speg/ 到 lib/python3（s3transfer 范式）

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 纯 Python：无编译
        apply_conandata_patches(self)

    def package(self):
        src = os.path.join(self.source_folder, "speg")
        dest = os.path.join(self.package_folder, "lib", "python3")
        if os.path.isdir(src):
            os.makedirs(dest, exist_ok=True)
            shutil.copytree(src, os.path.join(dest, "speg"),
                            dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(
                                "__pycache__", "*.pyc"))
        # 源码包无 LICENSE 文件（PKG-INFO 声明 MIT）——不复制许可证文件

    def package_info(self):
        self.cpp_info.libs = []
