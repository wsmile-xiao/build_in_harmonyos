#!/usr/bin/env python3
"""Conan test recipe — lzip CLI 行为断言（压缩/解压/一致性/错误路径）。"""
import os
import struct
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run


class LzipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("交叉构建无法运行，消费者运行时断言按协议跳过")
            return
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(self.recipe_folder, "test_lzip.py")
        bindir = os.path.join(dep.package_folder, "usr", "bin")
        self.run(f'"{sys.executable}" "{script}" "{bindir}"')
