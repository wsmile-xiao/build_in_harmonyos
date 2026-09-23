#!/usr/bin/env python3
"""test_package for device-tree-compiler 1.7.2 — 编译链接 libfdt 校验 magic，并运行 fdtdump --version。"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class DeviceTreeCompilerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["device-tree-compiler"].package_folder
        self.run(
            'clang test.c -o test_dtc -I "{pkg}/include" "{pkg}/lib/libfdt.a"'.format(pkg=pkg)
        )

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        pkg = self.dependencies["device-tree-compiler"].package_folder
        fdtdump = os.path.join(pkg, "bin", "fdtdump")
        if not os.path.isfile(fdtdump):
            raise ConanException(f"fdtdump binary missing: {fdtdump}")
        self.run(f'./test_dtc "{fdtdump}"')