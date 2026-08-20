#!/usr/bin/env python3
"""test_package for perl-xml-sax 1.02 — 驱动独立测试脚本。"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class PerlXmlSaxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        # 遍历所有依赖（含 perl-xml-sax-base 提供 XML::SAX::Exception），
        # 收集 @INC 根注入 PERL5LIB
        sites = []
        for _ref, dep in self.dependencies.items():
            for root, _dirs, files in os.walk(dep.package_folder):
                if "Exception.pm" in files:
                    sites.append(os.path.dirname(os.path.dirname(os.path.dirname(root))))
                    break
        if not sites:
            raise ConanException("XML/SAX/Exception.pm not found in deps")
        # test_xmlsax.py 是 L0c 独立测试源（.py 被静态扫描识别），
        # 真实 API 检查在脚本内（perl 加载 + 构造 Exception）
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_xmlsax.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_xmlsax.py missing: {test_script}")
        self.run(
            f"python3 '{test_script}' '{':'.join(sites)}'",
            env="conanrun")
