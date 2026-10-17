#!/usr/bin/env python3
"""Conan test_package — kamailio-uuid L1 消费者视角测试。

uuid.so 由 kamailio 二进制运行时 loadmodule 加载（$u(...) 伪变量在 SIP 配置
脚本中求值），无法脱离 kamailio 进程独立执行，故按产物结构做实质校验：
ELF 架构、libuuid 静态链入证据（uuid_generate/uuid_unparse 导出符号）、
模块 API 导出符号、许可证随包、宿主路径泄漏检查。
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioUuidTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对打包产物 uuid.so 做真实检查
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "uuid.so")
        assert os.path.isfile(module), f"uuid.so not found at {module}"
        self.output.info(f"uuid.so found: {module}")

        checker = os.path.join(self.source_folder, "check_uuid.py")
        env = Environment()
        env.define("KAMAILIO_UUID_MODULE", module)
        env.define("KAMAILIO_UUID_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
