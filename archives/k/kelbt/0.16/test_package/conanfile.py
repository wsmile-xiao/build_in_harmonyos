#!/usr/bin/env python3
"""Conan test_package for kelbt — runs the installed kelbt binary end-to-end.

kelbt 是 CLI 工具（无库/头文件安装），test() 通过 bash 执行 test.sh，
验证 `kelbt --version` 与「用 .kh 语法文件生成 parser header」这一核心能力。
"""
import os
import shutil

from conan import ConanFile


class KelbtTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        # 直接以完整路径的 bash 执行 test.sh（避免内层再查 PATH 里的 bash）。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} test.sh", env="conanrun")
