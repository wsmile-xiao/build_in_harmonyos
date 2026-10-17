#!/usr/bin/env python3
"""Conan test_package for console-cyrillic 0.9（house 模板，console-setup 先例）。"""
import os
import shutil

from conan import ConanFile


class ConsoleCyrillicTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_console_cyrillic.sh")
        # perl 脚本（#!/usr/bin/env perl）——perl 由 hnp 提供
        # /data/service/hnp/bin/perl，run 命令显式 PATH 前缀；
        # 包目录显式传参（脚本在 source_folder，cwd 是 package_folder，
        # dirname($0)/.. 会解析到 recipe 目录）
        self.run(
            f'PATH=/data/service/hnp/bin:$PATH "{bash}" "{script}" '
            f'"{pkg_folder}"',
            env="conanrun",
            cwd=pkg_folder,
        )
