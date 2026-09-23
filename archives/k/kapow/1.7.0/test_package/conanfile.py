#!/usr/bin/env python3
"""Conan test_package — kapow 1.7.0 (pure-executable consumer).

kapow 是纯可执行包（GUI/Qt6，无 lib/ 产物），没有可供 find_package
链接的库。因此 L1 消费者不用 CMakeDeps/CMakeToolchain 链接库（那会报
"Library not found"，即 G2 E225），而是直接运行安装的 kapow 二进制
（offscreen smoke：Qt 初始化成功并进入事件循环即可）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment


class KapowTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能直接执行 ELF 二进制，用 bash 包装。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pkg = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(pkg.package_folder, *pkg.cpp_info.bindirs)
        env = Environment()
        env.define("CONAN_BIN_DIRS", bindir)
        self.run(f"env CONAN_BIN_DIRS={bindir} {bash} {os.path.join(self.source_folder, 'test.sh')}",
                 env="conanrun")
