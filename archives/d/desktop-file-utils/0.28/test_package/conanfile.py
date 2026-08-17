#!/usr/bin/env python3
"""test_package for desktop-file-utils 0.28 — 编译运行 test.c 验证 CLI 可执行。"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class DesktopFileUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self.run("clang test.c -o test_desktop_file_utils")

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        pkg = self.dependencies["desktop-file-utils"].package_folder
        bin_path = os.path.join(pkg, "bin", "desktop-file-validate")
        if not os.path.isfile(bin_path):
            raise ConanException(f"desktop-file-validate binary missing: {bin_path}")
        self.run(f'"{bin_path}" --version')
        self.run(f'./test_desktop_file_utils "{bin_path}"')