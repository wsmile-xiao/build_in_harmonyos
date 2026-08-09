#!/usr/bin/env python3
"""Conan test_package — aaudit-server 0.7.2 L1 smoke test."""
import os
import shutil
from conan import ConanFile


class AauditServerTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 验证 aaudit 可执行文件存在且可运行
        aaudit_bin = os.path.join(self.dependencies["aaudit-server"].package_folder,
                                  "usr", "bin", "aaudit")
        self.output.info(f"验证 aaudit 可执行文件: {aaudit_bin}")
        self.run(f"test -x {aaudit_bin}", env="conanrun")

        # 验证 aaudit --help 能正常输出（运行时可用时；否则 test.sh 做静态校验）
        if shutil.which("lua5.2") is not None:
            self.run(f"lua5.2 {aaudit_bin} --help 2>&1 | head -5", env="conanrun")

        # 验证配置文件存在
        config_file = os.path.join(self.dependencies["aaudit-server"].package_folder,
                                   "etc", "aaudit", "aaudit.json")
        self.run(f"test -f {config_file}", env="conanrun")

        # 验证 Lua 模块存在
        lua_module = os.path.join(self.dependencies["aaudit-server"].package_folder,
                                  "usr", "share", "lua", "5.2", "aaudit", "common.lua")
        self.run(f"test -f {lua_module}", env="conanrun")

        # 运行 shell 冒烟测试（L0c 要求 test_package 含测试源文件，test.sh 已注册）
        pkg_folder = self.dependencies["aaudit-server"].package_folder
        self.run(f'bash test.sh "{pkg_folder}"', env="conanrun")