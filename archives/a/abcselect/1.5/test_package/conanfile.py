#!/usr/bin/env python3
"""Conan test_package for abcselect 1.5.

abcselect is a Perl script tool — the test verifies the script exists
and responds to --help.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AbcselectTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["abcselect"]
        bindir = os.path.join(dep.package_folder, "bin")
        abcselect = os.path.join(bindir, "abcselect")

        if not os.path.isfile(abcselect):
            raise ConanException(f"abcselect not found: {abcselect}")

        self.output.info(f"  abcselect: {os.path.getsize(abcselect)} bytes")

        # abcselect 是 Perl 脚本，shebang 指向 /usr/bin/perl（OHOS 上不存在），
        # 直接执行会失败（exit 126）。改用 perl 依赖的解释器显式执行。
        perl_dep = self.dependencies["perl"]
        perl_bin = os.path.join(perl_dep.package_folder, "bin", "perl")
        if not os.path.isfile(perl_bin):
            raise ConanException(f"perl interpreter not found: {perl_bin}")

        # Run -? (help) to verify the script works. 注意：abcselect 仅识别
        # "-?" 为 help 选项（返回 0）；"--help" 未被脚本识别（返回 1）。
        result = self.run(f"{perl_bin} {abcselect} -?", env="conanrun", ignore_errors=True)
        if result >= 128 or result == 127:
            raise ConanException(f"abcselect crashed (exit code {result})")
        if result != 0:
            raise ConanException(f"abcselect -? failed (exit code {result})")
        self.output.info("abcselect -?: OK")