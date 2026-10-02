#!/usr/bin/env python3
"""Conan test_package — tua 4.3

实质调用被测包（R34）：对合成的 Taylor UUCP spool 运行安装后的 tua，
校验报表输出结构；测试逻辑与用例统计在 test_tua.sh。
"""
import os

from conan import ConanFile


class TuaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["tua"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        script = os.path.join(self.source_folder, "test_tua.sh")
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，用 bash 包装执行
        bash = "/data/service/hnp/bin/bash"
        if not os.path.exists(bash):
            bash = "bash"
        self.run(f'{bash} "{script}" "{bin_dir}"', env="conanrun")
