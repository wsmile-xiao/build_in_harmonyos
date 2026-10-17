#!/usr/bin/env python3
"""test_package — sili 0.3.0 消费者 L1 测试。

链接安装的静态库 libsili.a，调用公开 API 验证消费者视角可用性。
CI 通过 conan create 自动运行（五级测试体系的 L1）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SiliTestConan(ConanFile):
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
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_sili')}", env="conanrun")
