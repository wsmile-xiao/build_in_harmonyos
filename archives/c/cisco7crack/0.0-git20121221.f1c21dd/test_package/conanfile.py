#!/usr/bin/env python3
"""Conan test_package — cisco7crack CLI behaviour verification.

cisco7crack is a CLI tool, not a library, so the test binary receives the path
of the installed `cisco7crack` executable and drives it end-to-end (R34):
known-answer decryption, deterministic encryption, round-trip and the
illegal-input exit path.
"""
import os

from conan import ConanFile


class Cisco7CrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        # C 测试不收 C++ 标准开关；gnu99 保证 POSIX 声明可见。
        self.run(f"{cc} -O2 -std=gnu99 test.c -o test_probe")

    def test(self):
        crack_bin = os.path.join(
            self.dependencies["cisco7crack"].package_folder, "bin", "cisco7crack"
        )
        self.run(f'./test_probe "{crack_bin}"', env="conanrun")
