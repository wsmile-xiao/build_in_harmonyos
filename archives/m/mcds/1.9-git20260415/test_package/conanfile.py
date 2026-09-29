#!/usr/bin/env python3
"""test_package/conanfile.py — mcds 1.9-git20260415 消费者测试（L1）。

被测对象是命令行程序（package_type=application），所以这里不编译 C 测试
程序，而是直接用被测包**绝对路径**下的 bin/mcds 跑功能断言（R34：必须
真实执行被测包产物）。

同时把该包的 package_folder 一起传给 test.sh：构建主机上 harmonybrew 自带
同名 mcds，只比"路径看起来像"并不可靠，必须由 conan 解析出的 package_folder
做前缀核对，才能证明跑的是本次交付的产物。

运行期依赖（libcurl / libxml2）由 env="conanrun" 提供 LD_LIBRARY_PATH：
实测在 conan 环境外直接执行该二进制会报
`Error loading shared library libcurl.so` ⇒ 这是真实的动态链接依赖，
不是测试脚本的装饰。
"""
import os

from conan import ConanFile


class McdsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["mcds"].package_folder
        mcds = os.path.join(pkg_folder, "bin", "mcds")
        script = os.path.join(self.source_folder, "test.sh")
        runner = "/bin/sh" if os.path.exists("/bin/sh") else "sh"
        self.run('{sh} "{script}" "{bin}" "{pkg}"'.format(
            sh=runner, script=script, bin=mcds, pkg=pkg_folder),
            env="conanrun")
