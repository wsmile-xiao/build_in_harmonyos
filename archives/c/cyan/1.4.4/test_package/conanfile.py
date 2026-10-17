#!/usr/bin/env python3
"""Test package — cyan 1.4.4 (python)"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CyanTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # cpp_info.bindirs 是消费者视角 (test_package 是依赖 cyan 的消费者),
        # self.cpp.build.bindirs 是 build 时视角 (test_package 自身还没有产物).
        cyan_dep = self.dependencies[self.tested_reference_str]
        bindir = cyan_dep.cpp_info.bindirs[0]
        bin_path = os.path.join(bindir, "cyan")
        self.run(f'"{bin_path}" --help', env="conanrun")
