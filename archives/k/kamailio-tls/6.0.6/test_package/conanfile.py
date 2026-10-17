#!/usr/bin/env python3
"""Conan test_package — kamailio-tls L1 消费者视角测试。

tls.so 由 kamailio 二进制运行时 dlopen（TLS 握手需运行中的 kamailio + 证书配置），
故按产物结构做实质校验：ELF 架构、OpenSSL 静态链入证据（SSL 导出符号）、
模块 API 导出符号、许可证与配置文件、宿主路径泄漏检查。
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioTlsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对打包产物 tls.so 做真实检查
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "tls.so")
        assert os.path.isfile(module), f"tls.so not found at {module}"
        self.output.info(f"tls.so found: {module}")

        checker = os.path.join(self.source_folder, "check_tls.py")
        env = Environment()
        env.define("KAMAILIO_TLS_MODULE", module)
        env.define("KAMAILIO_TLS_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
