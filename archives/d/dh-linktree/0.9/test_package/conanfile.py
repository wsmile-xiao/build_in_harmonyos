#!/usr/bin/env python3
"""Conan test_package for dh-linktree — verifies installed files + perl
syntax + best-effort functional smoke.

test_type="explicit"：本地 noexec 沙箱不自动跑脚本，运行验证交 CI
（build_and_test.sh 显式调用）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["dh-linktree"].package_folder
            # 收集依赖包（debhelper/dpkg）路径——PERL5LIB 需含依赖包的
            # perl 库目录（Dh_Lib 来自 debhelper、Dpkg::IPC 来自 dpkg）
            dep_dirs = [d.package_folder for n, d in self.dependencies.items()
                        if d.ref.name != "dh-linktree"]
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_dh_linktree.py")
            args = [sys.executable, test_script, pkg] + dep_dirs
            self.run(" ".join(f'"{a}"' for a in args), env="conanrun")
