#!/usr/bin/env python3
"""hoedown 3.0.7 test_package — 消费者视角验证。

构建一个调用 libhoedown 公共 API（hoedown_html_renderer_new /
hoedown_document_new / hoedown_document_render）渲染 Markdown 的小程序，
并在 test() 中真实运行该程序（L0d 要求 test() 含 self.run()，不能只编译或
只打印）：程序本身断言输出包含 <h1>，失败时以非零退出码返回。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HoedownTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # L0d/R34: 真实运行 CMake 构建的测试程序，验证包可被消费且行为正确
        self.run(os.path.join(self.build_folder, "test_hoedown"), env="conanrun")
