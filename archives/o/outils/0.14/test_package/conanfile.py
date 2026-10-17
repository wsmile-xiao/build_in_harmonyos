#!/usr/bin/env python3
"""test_package for outils 0.14 — 运行 test.sh 实际执行安装后的全部 CLI 工具（R34）。"""
import os

from conan import ConanFile


class OutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
