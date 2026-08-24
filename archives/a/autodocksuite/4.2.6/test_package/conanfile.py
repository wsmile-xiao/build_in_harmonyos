#!/usr/bin/env python3
"""test_package — autodocksuite 4.2.6 consumer test (R34).

L1 test:
1. 编译并运行 test.c（L0c 测试源文件载体）；
2. 应用验证：autodock --help 与 autogrid 可执行（--help 输出用法）。
"""
import os

from conan import ConanFile


class AutodocksuiteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_autodocksuite")
        # 路径引号包裹（工作目录可能含空格/括号——本地验证实测
        # syntax error: unexpected '('——CI 目录无空格不受影响）
        self.run(f"'{cc}' '{src}' -o '{out}'")

    def test(self):
        exe = os.path.join(self.build_folder, "test_autodocksuite")
        self.run(f"'{exe}'")
        bindir = os.path.join(
            self.dependencies["autodocksuite"].package_folder, "bin")
        autodock = os.path.join(bindir, "autodock4")
        autogrid = os.path.join(bindir, "autogrid4")
        self.run(f"test -x '{autodock}'")
        self.run(f"test -x '{autogrid}'")
        # --help 输出用法（无输入文件时打印 usage）
        self.run(f"'{autodock}' --help", env="conanrun")
        self.run(f"'{autogrid}' --help", env="conanrun")
