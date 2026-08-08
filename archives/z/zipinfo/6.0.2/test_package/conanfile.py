#!/usr/bin/env python3
"""Conan test_package for zipinfo 6.0 — verifies the zipinfo binary works.

Tests that the zipinfo executable can list the contents of a ZIP archive
(R34: test must substantially depend on the tested package by executing
its binary and validating output).
"""
import os

from conan import ConanFile


class ZipinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 使用包内 zipinfo 二进制（package_folder），而非系统 PATH，
        # 确保 L1e 负向测试（sabotage 包产物后重跑）能真实失败
        dep = self.dependencies["zipinfo"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        # OHOS: /system/bin/sh (mksh) 不能可靠执行 ELF 二进制，用 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh {bin_dir}", env="conanrun")