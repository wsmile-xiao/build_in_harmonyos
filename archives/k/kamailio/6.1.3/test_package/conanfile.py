#!/usr/bin/env python3
"""Conan test_package — kamailio core L1 消费者视角测试。

kamailio 主二进制的完整 SIP 服务运行需配置文件与运行时环境，故按产物结构
做实质校验：ELF 架构/PIE、版本标识、NEEDED 依赖面（仅 libc.so，musl 内置
pthread/m/dl）、无 RPATH/RUNPATH 泄漏、许可证随包（与 6.0.6 模块族口径一致）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对打包产物 bin/kamailio 做真实检查
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "kamailio")
        assert os.path.isfile(binary), f"kamailio not found at {binary}"
        self.output.info(f"kamailio found: {binary}")

        checker = os.path.join(self.source_folder, "check_kamailio.py")
        env = Environment()
        env.define("KAMAILIO_BINARY", binary)
        env.define("KAMAILIO_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
