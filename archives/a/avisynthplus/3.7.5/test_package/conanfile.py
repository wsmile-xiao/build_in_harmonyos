#!/usr/bin/env python3
"""test_package — avisynthplus 3.7.5 consumer test (R34).

L1 test:
1. 编译并运行 test.cpp（链接 libavisynth，验证头文件/库可用）；
2. 应用验证：libavisynth 库文件存在。
"""
import os

from conan import ConanFile


class AvisynthplusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = ccs.get("cpp") or "clang++"
        src = os.path.join(self.source_folder, "test.cpp")
        out = os.path.join(self.build_folder, "test_avisynthplus")
        pkg = self.dependencies["avisynthplus"].package_folder
        self.run(
            f"{cxx} {src} -o {out} -std=c++17 "
            f"-I{pkg}/include -L{pkg}/lib -lavisynth")

    def test(self):
        exe = os.path.join(self.build_folder, "test_avisynthplus")
        self.run(exe, env="conanrun")
        lib = os.path.join(
            self.dependencies["avisynthplus"].package_folder, "lib")
        self.run(f"test -e {lib}/libavisynth.so")
