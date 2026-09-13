#!/usr/bin/env python3
"""Conan test_package — desproxy 0.1.0 (executable smoke test).

desproxy 是命令行工具集（无库 API），test() 实际执行 5 个二进制，
验证安装产物可运行（R34：必须实质执行被测包二进制）。
"""
import os

from conan import ConanFile


class DesproxyTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF；用 bash 包裹执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
