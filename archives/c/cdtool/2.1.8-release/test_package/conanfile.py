#!/usr/bin/env python3
"""Conan test_package for cdtool 2.1.8-release — 消费者视角验证安装产物。

test() 直跑 test_cdtool.py，对**已安装包目录**做校验：
安装布局（lib/cdtool/cdtool + bin/ 5 独立产物 + 10 别名符号链接 + 16 份
手册页）、OHOS 产物属性（aarch64 PIE + musl 加载器）、以及 4 个刚安装
二进制的真实运行。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class CdtoolTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_folder = self.dependencies["cdtool"].package_folder
        script = os.path.join(self.source_folder, "test_cdtool.py")
        self.run('python3 "%s" "%s"' % (script, pkg_folder), env="conanrun")
