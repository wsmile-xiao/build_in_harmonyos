#!/usr/bin/env python3
"""test_package for ol 2.7 — 真实消费者验证。

1. 编译并运行 C 消费者，用 <ol/ol.h> 的嵌入 API 调用 libol.so 并断言求值结果；
2. 用安装好的 ol 解释器运行 harness.scm（覆盖 OL_HOME 标准库导入 + 结果断言）；
3. 运行 olvm --version，确认剥离后重新签名的虚拟机可执行。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class OlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _compiler(self):
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp.get("c") or "clang"

    def build(self):
        pkg = self.dependencies["ol"].package_folder
        out = os.path.join(self.build_folder, "embed_test")
        self.run(
            f'{self._compiler()} embed_test.c -o "{out}" '
            f'-I"{pkg}/include" -L"{pkg}/lib" -lol -Wl,-rpath,"{pkg}/lib"',
            cwd=self.source_folder,
        )

    def test(self):
        pkg = self.dependencies["ol"].package_folder
        ol_bin = os.path.join(pkg, "bin", "ol")
        olvm_bin = os.path.join(pkg, "bin", "olvm")
        harness = os.path.join(self.source_folder, "harness.scm")

        self.run(os.path.join(self.build_folder, "embed_test"), env="conanrun")
        self.run(f'"{ol_bin}" "{harness}"', env="conanrun")
        self.run(f'"{olvm_bin}" --version', env="conanrun")
