#!/usr/bin/env python3
"""test_package for tty-clock 2.3 — 编译运行 test.c 验证 CLI 可执行。"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TtyClockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self.run("clang test.c -o test_tty_clock")

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        # Use the full path to the tty-clock binary from THIS package
        pkg = self.dependencies["tty-clock"].package_folder
        bin_path = os.path.join(pkg, "bin", "tty-clock")
        if not os.path.isfile(bin_path):
            raise ConanException(f"tty-clock binary missing: {bin_path}")
        self.run(f'"{bin_path}" -v')
        self.run(f'./test_tty_clock "{bin_path}"')