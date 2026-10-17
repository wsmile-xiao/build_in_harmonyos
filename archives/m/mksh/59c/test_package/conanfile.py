#!/usr/bin/env python3
"""Conan test_package for mksh 59c — 以使用者身份运行打包后的 mksh 并断言行为。"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import load, save
from conan.tools.layout import basic_layout


class MkshTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(pkg, "bin", "mksh")
        if not os.path.isfile(binary):
            raise ConanException(f"mksh binary is missing from the package: {binary}")

        if not can_run(self):
            self.output.warning("cross-building: mksh cannot be executed on the build "
                                "host, the 10 consumer assertions are skipped")
            return

        os.makedirs(self.build_folder, exist_ok=True)
        script = os.path.join(self.source_folder, "test_mksh.sh")
        # HMDFS 上 chmod 不生效，且脚本可能带 CRLF —— 归一化后用 sh 显式执行
        text = load(self, script).replace("\r\n", "\n").replace("\r", "\n")
        normalized = os.path.join(self.build_folder, "test_mksh.sh")
        save(self, normalized, text)
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(f'"{shell}" "{normalized}" "{binary}"', env="conanrun")
