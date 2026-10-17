#!/usr/bin/env python3
"""test_package — bogofilter 1.2.5 consumer test (R34).

L1 test:
1. 编译并运行 test.cpp——它**真正调用包内 bogofilter 二进制**做端到端
   贝叶斯验证（训练 ham/spam + 分类 spam 特征邮件，断言退出码），
   非空壳打印（R34）；
2. 检查包内 bogofilter/bogoutil 可执行文件存在。
"""
import os

from conan import ConanFile


class BogofilterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cpp = ccs.get("cpp") or "clang++"
        src = os.path.join(self.source_folder, "test.cpp")
        out = os.path.join(self.build_folder, "test_bogofilter")
        self.run(f"{cpp} {src} -o {out}")

    def test(self):
        # 包内二进制检查
        bindir = os.path.join(
            self.dependencies["bogofilter"].package_folder, "bin")
        bogofilter = os.path.join(bindir, "bogofilter")
        bogoutil = os.path.join(bindir, "bogoutil")
        self.run(f"test -x {bogofilter}")
        self.run(f"test -x {bogoutil}")
        # 端到端测试：传 bogofilter 路径 + 词库路径（放 build 目录避免污染）
        exe = os.path.join(self.build_folder, "test_bogofilter")
        bd = os.path.join(self.build_folder, "wordlist.db")
        self.run(f"{exe} {bogofilter} {bd}")
