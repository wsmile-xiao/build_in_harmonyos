#!/usr/bin/env python3
"""Conan test_package for badread 0.4.2.

R34: test must substantively depend on the package under test.
badread is a console application (entry point: badread = badread.__main__:main).
We invoke the installed `badread --version` to verify the wrapper and package layout work.
"""
import os

from conan import ConanFile


class BadreadTestConan(ConanFile):
    # 纯 Python 应用测试，无需 CMake
    test_type = "explicit"
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: 实质依赖被测包 — 调用 bin/badread --version
        badread_dep = self.dependencies["badread"]
        badread_bin = os.path.join(badread_dep.package_folder, "bin", "badread")
        self.run(f'"{badread_bin}" --version', env="conanrun")  # 期望输出 "Badread v0.4.2"
