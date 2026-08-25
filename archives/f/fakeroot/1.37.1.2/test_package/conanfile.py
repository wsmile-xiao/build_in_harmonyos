#!/usr/bin/env python3
"""Conan test_package for fakeroot 1.37.1.2 — verifies fakeroot binary works."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class FakerootTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bindir = self.dependencies["fakeroot"].package_folder
        # fakeroot 主程序（--version 不依赖真实 root 权限）——
        # 测试源 test_fakeroot.sh（L0c 门禁要求 test_package 有测试源）
        fakeroot = os.path.join(bindir, "bin", "fakeroot")
        if not os.path.isfile(fakeroot):
            raise RuntimeError(f"fakeroot binary not found: {fakeroot}")
        script = os.path.join(self.source_folder, "test_fakeroot.sh")
        self.run(f'bash "{script}" "{bindir}"', env="conanrun")
