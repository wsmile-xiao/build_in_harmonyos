#!/usr/bin/env python3
"""Conan test_package — ghex 46.0 consumer test.

验证 ghex 可执行文件已正确安装，且链接了 GTK4 / libadwaita 图形栈。

HMDFS/SELinux 限制导致 ghex 二进制无法直接执行（Operation not permitted），
因此 test_ghex.sh 采用 readelf 静态验证：ELF 头 + 架构 + 动态依赖链。
"""
import os

from conan import ConanFile


class GhexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        ghex_bin = os.path.join(dep.cpp_info.bindir, "ghex")

        assert os.path.isfile(ghex_bin), f"ghex binary not found: {ghex_bin}"
        size = os.path.getsize(ghex_bin)
        assert size > 0, f"ghex binary is empty: {ghex_bin}"
        self.output.info(f"[test] ghex binary: {ghex_bin} ({size} bytes)")

        script = os.path.join(self.source_folder, "test_ghex.sh")
        assert os.path.isfile(script), f"test_ghex.sh not found: {script}"
        self.run(f"sh {script} {ghex_bin}", env="conanrun")

        self.output.info("[test] test_ghex.sh PASSED")
