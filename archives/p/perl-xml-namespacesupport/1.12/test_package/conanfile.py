#!/usr/bin/env python3
"""test_package for perl-xml-namespacesupport 1.12 — 驱动独立测试脚本。"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class PerlXmlNamespaceSupportTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        pkg = self.dependencies["perl-xml-namespacesupport"].package_folder
        # 定位 XML/NamespaceSupport.pm 的 @INC 根
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "NamespaceSupport.pm" in files:
                site = os.path.dirname(os.path.dirname(root))
                break
        if not site:
            raise ConanException("XML/NamespaceSupport.pm not found in package")
        # test_namespacesupport.py 是 L0c 独立测试源（.py 被静态扫描识别），
        # 真实 API 检查在脚本内（perl 加载 + 最小 API 调用）
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_namespacesupport.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_namespacesupport.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
