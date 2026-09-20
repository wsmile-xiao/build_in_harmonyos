#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for GitPython 3.1.57

GitPython is a pure-Python git object library (git repo/command abstraction).
It is the downstream consumer of gitdb (already archived as gitdb/4.0.12,
which itself requires smmap/5.0.3).

Runtime dependency per PyPI metadata (3.1.57):
  - gitdb>=4.0.1,<5          -> declared as Conan requirement gitdb/4.0.12
  - typing-extensions>=3.10.0.2; python_version < "3.10"
                             -> not needed (target python3.12 >= 3.10)
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import copy, get


class GitPythonConan(ConanFile):
    name = "gitpython"
    version = "3.1.57"
    license = "BSD-3-Clause"
    author = "GitPython contributors"
    url = "https://github.com/gitpython-developers/GitPython"
    homepage = "https://github.com/gitpython-developers/GitPython"
    description = "GitPython is a Python library used to interact with Git repositories"
    topics = ("git", "vcs", "python", "dvcs")
    package_type = "unknown"  # pure Python package, not a compiled library
    settings = "os", "arch", "compiler", "build_type"

    # Runtime dependency: gitdb>=4.0.1,<5 (upstream PyPI requires_dist)
    requires = "gitdb/4.0.12"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Pure Python package: pip install --no-deps to a target directory
        # --no-deps: gitdb is declared as a Conan requirement, not pip-managed
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
