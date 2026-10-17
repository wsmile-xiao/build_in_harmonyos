#!/usr/bin/env python3
"""Conan test_package — fondu 0.0.20060102

Tests the fondu binary. fondu is a command-line tool set (not a library),
so we test the binary directly: running it with an unknown option prints
the Usage message to stderr and exits 0. The test script also verifies
the Usage output content (not just the exit code).
"""
import os

from conan import ConanFile


class FonduTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        bin_dir = self.dependencies["fondu"].cpp_info.bindirs[0]
        fondu_bin = os.path.join(bin_dir, "fondu")
        # 调用 test.sh 验证 fondu -h 打印 Usage 且退出码 0（输出内容断言）
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'bash "{test_script}" "{fondu_bin}"', env="conanrun")
