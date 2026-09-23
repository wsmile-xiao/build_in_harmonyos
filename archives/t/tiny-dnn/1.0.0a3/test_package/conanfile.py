#!/usr/bin/env python3
"""Compile and run a tiny-dnn consumer against the OHOS package.

tiny-dnn 是 header-only，消费者只需一个 `-I<include 根>`：三棵目录
（tiny_dnn/ + cereal/ + third_party/）并排装在同一根下，`<cereal/...>`
角括号包含与 `"third_party/..."` 相对包含都能解析。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TinyDNNTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["tiny-dnn"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")

        source = os.path.join(self.source_folder, "test_tiny_dnn.cpp")
        executable = os.path.join(self.build_folder, "test_tiny_dnn")

        self.run(
            '"{}" -std=c++17 -O1 -I"{}" "{}" -pthread -o "{}"'.format(
                cxx,
                os.path.join(pkg.package_folder, "include"),
                source,
                executable,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run('"{}"'.format(executable), env="conanrun")
