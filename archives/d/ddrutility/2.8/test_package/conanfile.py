#!/usr/bin/env python3
"""Conan test_package for ddrutility — runs test.sh which executes the five CLI tools."""

import os
import shutil

from conan import ConanFile


class DdrutilityTestConan(ConanFile):
    """test_package for ddrutility executable tool set — verifies the five binaries run."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不适合承载该测试脚本；用 bash 执行
        # （绝对路径优先，缺失时回退 PATH 中的 bash）。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        bindir = os.path.join(self.dependencies["ddrutility"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{script}" "{bindir}"', env="conanrun")
