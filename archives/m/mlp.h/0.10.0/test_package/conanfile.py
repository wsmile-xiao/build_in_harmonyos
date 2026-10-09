#!/usr/bin/env python3
"""Conan test_package — mlp.h 0.10.0 (header-only C library)

Header-only: compile a small C consumer that #defines MLP_IMPLEMENTATION,
includes the packaged MLP.h, trains an XOR network via the public API and
verifies the trained outputs are close to the expected truth table (R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy


class MlpHTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # header-only: no configure/build system; compile the consumer directly
        compiler = self.conf.get("tools.build:compiler_executables", default={})
        cc = compiler.get("c", "cc")
        src = os.path.join(self.source_folder, "test_mlp.c")
        exe = os.path.join(self.build_folder, "test_mlp")
        inc = os.path.join(self.dependencies["mlp.h"].package_folder, "include")
        # Conan 2.x: self.run 默认对非零退出码抛错（不接收 check= 参数）
        self.run(f"{cc} -std=c99 -O2 -I{inc} {src} -o {exe} -lm")

    def test(self):
        exe = os.path.join(self.build_folder, "test_mlp")
        self.run(exe, env="conanrun")
