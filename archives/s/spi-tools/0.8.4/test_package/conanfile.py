#!/usr/bin/env python3
"""Conan test_package for spi-tools 0.8.4.

Runs test.sh against the packaged executables: real invocations of spi-config
and spi-pipe whose exit codes and stderr text decide the verdict (R34 — not a
print-only stub).
"""
import os

from conan import ConanFile


class SpiToolsTestConan(ConanFile):
    """Consumer-side test for the spi-tools executables."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        tool = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(tool.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test.sh")
        # 显式用 /bin/sh：设备 hnp 的 bash 在 HMDFS 构建目录下 getcwd() 会失败（E386），
        # 本脚本只用 POSIX 构造，不需要 bash 扩展。
        self.run('BINDIR="%s" /bin/sh "%s"' % (bindir, script), env="conanrun")
