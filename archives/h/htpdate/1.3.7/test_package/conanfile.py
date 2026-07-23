#!/usr/bin/env python3
"""Conan test_package — htpdate 1.3.7

Tests the htpdate binary by checking version and help output.
htpdate is a command-line tool, not a library, so we test the binary directly.
"""
from conan import ConanFile


class HtpdateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # 运行 smoke test 脚本 (conanrun env 会将 htpdate bin/ 加入 PATH)
        self.run("sh test.sh", env="conanrun")
