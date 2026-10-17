#!/usr/bin/env python3
"""Conan test_package — kamailio-xml (xmlops) L1 消费者视角测试。

xmlops.so 由 kamailio 二进制运行时 dlopen（XML 伪变量求值需运行中的 kamailio
路由脚本），故按产物结构做实质校验：ELF 架构、libxml2 链入证据（xmlXPath
导出符号）、模块 API 导出符号、许可证、宿主路径泄漏检查。
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioXmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对打包产物 xmlops.so 做真实检查
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "xmlops.so")
        assert os.path.isfile(module), f"xmlops.so not found at {module}"
        self.output.info(f"xmlops.so found: {module}")

        checker = os.path.join(self.source_folder, "check_xmlops.py")
        env = Environment()
        env.define("KAMAILIO_XML_MODULE", module)
        env.define("KAMAILIO_XML_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
