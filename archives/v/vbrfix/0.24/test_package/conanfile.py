#!/usr/bin/env python3
"""Conan test_package — vbrfix 0.24（vbrfixc）

实质调用被测包（R34）：对合成 MP3 样本运行安装后的 vbrfixc 并校验产物结构。
测试逻辑与用例统计在 test_vbrfixc.sh（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class VbrfixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["vbrfix"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        script = os.path.join(self.source_folder, "test_vbrfixc.sh")
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，用 bash 包装执行
        bash = "/data/service/hnp/bin/bash"
        if not os.path.exists(bash):
            bash = "bash"
        self.run(f'{bash} "{script}" "{bin_dir}"', env="conanrun")
