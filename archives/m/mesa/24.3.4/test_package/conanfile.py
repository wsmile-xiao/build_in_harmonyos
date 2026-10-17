#!/usr/bin/env python3
"""Conan test_package — mesa 24.3.4 L1 消费者验证

test() 实际编译并运行 test_mesa：dlopen 被测包的 libGLESv2/libglapi 解析 GL
入口点（R34：实质依赖被测包，非空壳）。在 OHOS HNP 沙箱 dlopen 被 mmap 拒时
（E046 类平台限制，见 test.c 注释），回退为对打包库导出符号表的只读验证。
必须用 env="conanrun" 直跑二进制，否则 ctest 不注入 LD_LIBRARY_PATH，无法
定位打包库。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MesaTestConan(ConanFile):
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
        # 用 conanrun 环境直跑（LD_LIBRARY_PATH 指向打包库目录）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_mesa"), env="conanrun")
