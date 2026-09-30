#!/usr/bin/env python3
"""Conan test_package — ifcplusplus 0-git20190402.13744d5（Conan L1 消费者测试）。

CI 通过 `conan create` 自动调用本 test_package：
  1. 消费者视角链接已安装的 ifcplusplus 包（校验头文件/静态库/传递依赖完整）；
  2. 真实执行 test_ifcplusplus（消费者端到端：STEP 解析 + 几何遍历 + 回写回环）；
  3. 真实执行 test_ifcplusplus_ohos（鸿蒙专项消费者端到端：Carve CSG + GUID 编解码 + 多墙 STEP 回环）。

测试经 ctest 执行；交叉编译时由 profile 的 CMAKE_CROSSCOMPILING_EMULATOR
(ohos-aarch64-run) 驱动，CI/设备侧为原生执行。
本方法先用 `ctest -N` 断言套件非空，再执行全部用例——避免"空套件退出码 0"
被误当成"测试通过"（测试执行门：先证明用例真的跑起来了）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IfcplusplusTestConan(ConanFile):
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
        # ctest 的工作目录是构建目录（注册 add_test 的那一层）
        build_dir = self.build_folder
        # 1) 先证明套件非空：空套件时 ctest 退出码为 0，不能作为通过证据
        self.run(
            f'ctest --test-dir "{build_dir}" -N',
            env="conanrun",
        )
        # 2) 真实执行全部消费者用例，非 0 退出码即失败
        cmake.test()
