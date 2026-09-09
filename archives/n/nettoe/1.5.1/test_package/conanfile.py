#!/usr/bin/env python3
"""Conan test_package for nettoe — compile example.c and verify binary.

R34: test_package must contain real test source and actually execute the
tested binary. example.c (src/) executes `nettoe --version` via popen and
asserts the output contains "netToe 1.5.1".
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class NettoeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 从 profile conf 获取交叉编译器（tools.build:compiler_executables）
        cc = "clang"
        try:
            execs = self.conf.get("tools.build:compiler_executables", default={})
            if execs:
                if isinstance(execs, str):
                    execs = json.loads(execs)
                cc = execs.get("c", cc)
        except Exception:
            pass
        src = os.path.join(self.source_folder, "src", "example.c")
        out = os.path.join(self.build_folder, "example_test")
        os.makedirs(self.build_folder, exist_ok=True)
        self.run(f'"{cc}" "{src}" -o "{out}"')

    def test(self):
        if not can_run(self):
            return
        # nettoe 安装到 bin/（Autotools install，--prefix=package_folder）
        nettoe_bin = os.path.join(self.dependencies["nettoe"].package_folder,
                                  "bin", "nettoe")
        if not os.path.exists(nettoe_bin):
            # 部分版本安装到 usr/local/bin（默认 prefix）
            nettoe_bin = os.path.join(self.dependencies["nettoe"].package_folder,
                                      "usr", "local", "bin", "nettoe")
        test_bin = os.path.join(self.build_folder, "example_test")
        self.run(f'"{test_bin}" "{nettoe_bin}"', env="conanrun")