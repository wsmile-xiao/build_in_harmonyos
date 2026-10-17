#!/usr/bin/env python3
"""Conan recipe — roundup 0.0.6 (pure POSIX shell unit-test runner).

roundup is not a C/C++ library: the entire product is a single POSIX shell
script (`roundup.sh` -> `roundup`). Upstream "build" is `sh -n` syntax check
plus shebang rewrite; the package ships the script as a CLI tool (R38:
application => commands.json declared at software level).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class RoundupConan(ConanFile):
    name = "roundup"
    version = "0.0.6"
    description = "roundup - a unit testing tool for running roundup(5) test plans written in POSIX shell"
    license = "MIT"
    homepage = "https://bmizerany.github.io/roundup"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零依赖：纯 POSIX shell，仅要求目标环境存在 /bin/sh 与 coreutils
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 不依赖任何 shell 环境变量；上游 make 的全部动作即：
        #   1) `$(SHELL) -n roundup.sh` 语法检查
        #   2) sed 重写 shebang（目标 /bin/sh 与源一致，保持上游步骤以求忠实）
        #   3) chmod 0755
        src = self.source_folder
        self.run("sh -n roundup.sh", cwd=src)
        self.run(
            "sed \"s~#!/bin/sh~#!/bin/sh~\" roundup.sh > roundup && chmod 0755 roundup",
            cwd=src,
        )

    def package(self):
        copy(self, "roundup",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
