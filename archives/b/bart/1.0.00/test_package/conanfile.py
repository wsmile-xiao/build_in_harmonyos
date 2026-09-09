#!/usr/bin/env python3
"""test_package — bart 1.0.00 consumer test (R34).

L1 test:
1. 编译并运行 test.c（L0c 测试源文件载体）；
2. 应用验证：bart version 输出版本（--help/version 子命令）。
"""
import os

from conan import ConanFile


class BartTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_bart")
        self.run(f"{cc} {src} -o {out}")

    def test(self):
        exe = os.path.join(self.build_folder, "test_bart")
        self.run(exe)
        bindir = os.path.join(
            self.dependencies["bart"].package_folder, "bin")
        bart = os.path.join(bindir, "bart")
        self.run(f"test -x {bart}")
        # bart version 输出版本号
        self.run(f"{bart} version", env="conanrun")
