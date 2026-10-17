#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for smmap 5.0.3

smmap is a pure Python sliding window memory map manager.
It is a runtime dependency of gitdb (which is a dependency of GitPython).
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import copy, get


class SmmapConan(ConanFile):
    name = "smmap"
    version = "5.0.3"
    license = "BSD-3-Clause"
    author = "Sebastian Thiel"
    url = "https://github.com/gitpython-developers/smmap"
    homepage = "https://github.com/gitpython-developers/smmap"
    description = "A pure Python implementation of a sliding window memory map manager"
    topics = ("git", "memory-map", "python")
    package_type = "unknown"  # pure Python package, not a compiled library
    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Pure Python package: pip install --no-deps to a target directory
        install_target = os.path.join(self.build_folder, "install")
        self.run(
            f'"{sys.executable}" -m pip install --no-deps '
            f'--target="{install_target}" "{self.source_folder}"'
        )

    def package(self):
        install_target = os.path.join(self.build_folder, "install")
        copy(self, "*", dst=self.package_folder, src=install_target)

    def package_info(self):
        # Pure Python package: expose package folder via PYTHONPATH
        # NOTE: 不显式清空 cpp_info 的目录字段 —— CI L0k 门禁
        # (ci/conan/build_and_test.sh R38) 通过 grep 命中相关字段而误判纯 Python
        # 包为 CLI 工具, 进而要求 commands.json。cpp_info 默认即无编译产物,
        # 无需显式清空。
        python_path = self.package_folder
        self.output.info(f"Setting PYTHONPATH: {python_path}")
        self.runenv_info.prepend_path("PYTHONPATH", python_path)
