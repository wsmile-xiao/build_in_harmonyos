#!/usr/bin/env python3
"""Conan test_package for gnupg 2.5.22.

gnupg 是应用型包（application），测试方式为**真实执行**：
  - gpgv --version  （apt Release 签名验证实际使用的工具）
  - gpg  --version  （主程序）

实际断言由 test_gnupg.sh 承担（L0c 真实测试源文件）。
"""
import os

from conan import ConanFile


class GnupgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_gnupg.sh")
        # env="conanrun" 必需：gpgv 是动态链接可执行文件，运行时需在 LD_LIBRARY_PATH
        # 中带上依赖（libgpg-error / libgcrypt / libassuan / libksba / npth）的 lib 目录，
        # 否则报 `Error relocating .../bin/gpgv: gpgrt_vasprintf: symbol not found` 等。
        self.run(f"sh '{script}' '{pkg}'", env="conanrun")
