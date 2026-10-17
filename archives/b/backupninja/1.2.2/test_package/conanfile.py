#!/usr/bin/env python3
"""Conan test_package — backupninja 1.2.2.

验证 backupninja 可执行并实际运行（R34：实质调用被测包）。
调用 test_backupninja.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class BackupninjaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["backupninja"]
        # backupninja 安装到 sbin/（configure 默认 sbindir）
        bin_dir = os.path.join(pkg.package_folder, "usr", "sbin")
        for rel in ("usr", "sbin"), ("usr", "local", "sbin"), ("usr", "bin"):
            cand = os.path.join(pkg.package_folder, *rel)
            if os.path.exists(os.path.join(cand, "backupninja")):
                bin_dir = cand
                break
        script = os.path.join(self.source_folder, "test_backupninja.sh")
        self.run(f'sh "{script}" "{bin_dir}"')
