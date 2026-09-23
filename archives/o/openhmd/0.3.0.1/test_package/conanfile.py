#!/usr/bin/env python3
"""test_package: openhmd 消费者测试（消费打包后的 openhmd 包，黑盒）。

- build(): 用 conan CMakeDeps 生成的 openhmd::openhmd 目标编译消费者测试
- test():  在 VirtualRunEnv 运行时环境下执行测试二进制（hidapi 动态库可见）

上游测试（tests/unittests 11 个用例）在配方 build() 中以原始源码整体编译执行，
本 test_package 负责「打包产物 + 公共 API」这一层，两者互补不重复。
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class OpenhmdTestPackage(ConanFile):
    name = "openhmd-test-package"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_test_binary(self):
        for dirpath, _, filenames in os.walk(self.build_folder):
            if "openhmd_consumer_tests" in filenames:
                return os.path.join(dirpath, "openhmd_consumer_tests")
        return None

    def test(self):
        exe = self._find_test_binary()
        if not exe:
            raise ConanException("消费者测试二进制未找到（构建阶段应已失败）")
        # conanrun 环境包含 hidapi 依赖库目录（LD_LIBRARY_PATH）
        self.run('"%s"' % exe, env="conanrun")
