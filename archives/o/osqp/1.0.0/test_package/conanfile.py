#!/usr/bin/env python3
"""Conan test_package — osqp/1.0.0 L1 消费者测试。

由 conan create 自动执行：编译 test.c（真实调用 osqp_setup/osqp_solve/
osqp_update_data_vec 等公共 API）并运行二进制，断言上游示例 QP 的解析最优解。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OsqpTestConan(ConanFile):
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
        # 实际运行消费者测试二进制（test.c 真实调用 osqp_setup/osqp_solve 等 API）
        self.run("./test_osqp", env="conanrun")
