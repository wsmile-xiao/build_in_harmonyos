#!/usr/bin/env python3
"""Conan test_package for chkboot 1.3.

L1 消费者测试：对已安装的包执行 test_chkboot.sh（shell 用例套件）。
套件内容：包布局契约 + Debian autopkgtest 4 用例的场景等价移植 + 鸿蒙平台特有用例。
参见 test_package/MANIFEST.yml 与 reports/test-report.md。
"""
import os

from conan import ConanFile


class ChkbootTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(os.path.dirname(__file__), "test_chkboot.sh")
        # env="conanrun"：注入包 bin/ 到 PATH 与 CHKBOOT_CONF（package_info 的 runenv_info）
        self.run(f'bash "{script}" "{package_folder}"', env="conanrun")
