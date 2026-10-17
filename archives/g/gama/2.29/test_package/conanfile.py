#!/usr/bin/env python3
"""Conan test_package for gama 2.29 — Conan L1 official test.

Runs the installed gama-local CLI: --version, plus a real network
adjustment on an upstream test dataset (traverse-01-en-left.gkf from
tests/acord2/input), asserting the XML result contains adjusted points.
"""
import os
import shutil

from conan import ConanFile


class GamaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # 真实运行：--version + 上游测试数据完整平差 + 输出断言
        self.run(f"{bash} -c 'bash test_gama.sh'", env="conanrun")
