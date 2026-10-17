#!/usr/bin/env python3
"""test_package — xmlbird 1.2.14 消费者功能测试（R34）。

编译并运行 test.c：实质调用 libxmlbird 的公共 C API
（b_xml_parser_new/validate/get_root_tag + tag/attr 遍历 + encode/decode 往返）。
测试程序通过 _exit() 显式结束，绕过 OHOS 上 glib/gobject 运行时退出清理
的 SIGTRAP 平台限制（详见 notes.md）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XmlbirdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 直接运行测试二进制（独立于 ctest；ctest 在部分环境下不可用）
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_xmlbird")
        self.run(test_bin, env="conanrun")