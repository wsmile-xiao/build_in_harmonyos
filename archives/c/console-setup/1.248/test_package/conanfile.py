#!/usr/bin/env python3
"""Conan test_package for console-setup 1.248（house 模板，console-common 先例）。"""
import os
import shutil

from conan import ConanFile


class ConsoleSetupTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_console_setup.sh")
        # ckbcomp 是 perl 脚本（#!/usr/bin/env perl），perl 由 hnp 提供
        # /data/service/hnp/bin/perl——run 命令显式 PATH 前缀保证运行期
        # perl/bash 可见（不依赖 CI profile 的 PATH 继承）
        self.run(
            f'PATH=/data/service/hnp/bin:$PATH "{bash}" "{script}"',
            env="conanrun",
            cwd=pkg_folder,
        )
