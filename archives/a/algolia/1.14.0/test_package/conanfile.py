#!/usr/bin/env python3
"""Conan test_package for algolia 1.14.0 — 验证 algolia CLI 可执行.

algolia 是 Go CLI（application），test_package 通过 test.sh 冒烟测试：
algolia --version（验证 1.14.0 版本注入）与 algolia --help（usage 输出）。
R34 反空壳：真实执行被测包二进制并校验输出。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AlgoliaTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["algolia"].package_folder
        bin_path = os.path.join(package_folder, "bin", "algolia")
        if not os.path.isfile(bin_path):
            raise ConanException(f"algolia binary not found: {bin_path}")

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{test_script}" "{bin_path}"', env="conanrun")
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"algolia is not an ELF binary: {magic!r}"
            self.output.info(f"algolia binary exists and has ELF magic: {bin_path}")
