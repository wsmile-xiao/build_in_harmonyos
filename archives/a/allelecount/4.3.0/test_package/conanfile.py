#!/usr/bin/env python3
"""Conan test_package for allelecount — verify the alleleCounter binary runs."""
import os
from conan import ConanFile


class AllelecountTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 测试逻辑在 test_allelecount.sh(真正运行 alleleCounter 二进制),
        # 这里只执行该脚本。
        self.run("sh test_allelecount.sh", env="conanrun")
