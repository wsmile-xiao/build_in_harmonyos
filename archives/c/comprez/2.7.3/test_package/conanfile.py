#!/usr/bin/env python3
"""Conan test_package — comprez 2.7.3

comprez（z/zzcat）是可执行 shell 脚本压缩前端，无库文件，因此直接运行
脚本功能测试（test.sh）验证：z -h 用法、gzip/bzip2/xz/zip 压缩解压、
zzcat 解压、z -t 列表。
"""
import os

from conan import ConanFile


class ComprezTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS 环境用 bash 执行测试脚本
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")