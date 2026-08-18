#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for gitdb 4.0.12

gitdb is a pure-Python git object database.
It is a runtime dependency of GitPython.
Runtime dependency: smmap>=3.0.1,<6
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import copy, get


class GitdbConan(ConanFile):
    name = "gitdb"
    version = "4.0.12"
    license = "BSD-3-Clause"
    author = "Sebastian Thiel"
    url = "https://github.com/gitpython-developers/gitdb"
    homepage = "https://github.com/gitpython-developers/gitdb"
    description = "Git Object Database - a pure-Python git object database"
    topics = ("git", "object-database", "python")
    package_type = "unknown"  # pure Python package, not a compiled library
    settings = "os", "arch", "compiler", "build_type"

    # Runtime dependency: smmap>=3.0.1,<6
    requires = "smmap/5.0.3"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Pure Python package: pip install --no-deps to a target directory
        # --no-deps: smmap is declared as a Conan requirement, not pip-managed
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
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        python_path = self.package_folder
        self.output.info(f"Setting PYTHONPATH: {python_path}")
        self.runenv_info.prepend_path("PYTHONPATH", python_path)
