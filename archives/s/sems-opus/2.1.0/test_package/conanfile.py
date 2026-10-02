#!/usr/bin/env python3
"""Conan test_package — sems-opus 鸿蒙特有消费者测试 (L1 + 鸿蒙 dlopen 用例)。

CI 通过 conan create 自动调用。test() 运行随包分发的上游测试程序
sems_tests，并用 ctest 运行鸿蒙消费者用例 test_sems-opus：该用例按 SEMS
插件加载模型 dlopen 插件 opus.so、读取 amci_exports 导出结构，再实际执行
一次 init/encode/decode。插件绝对路径在 configure 阶段写入测试的
SEMS_OPUS_PLUGIN ctest 环境属性（由依赖包 libdir 推导）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SemsopusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 被测包的头文件目录与插件绝对路径交由 CMake：前者供 test.c 使用
        # amci.h/codecs.h 真实 ABI，后者写入 ctest 环境属性使 ctest 可直接运行
        include_dir = self.dependencies["sems-opus"].cpp_info.includedirs[0]
        plugin = os.path.join(self.dependencies["sems-opus"].cpp_info.libdirs[0],
                              "sems", "plug-in", "opus.so")
        cmake = CMake(self)
        cmake.configure(variables={"SEMS_OPUS_INCLUDE_DIR": include_dir,
                                   "SEMS_OPUS_PLUGIN": plugin})
        cmake.build()

    def test(self):
        # ① 上游测试（R51/rule4 真实执行）：运行随包分发的 sems_tests
        #    （fct.h 单体程序，11 个上游测试源文件编译而成）
        sems_tests = os.path.join(self.dependencies["sems-opus"].cpp_info.bindirs[0], "sems_tests")
        self.run(sems_tests, env="conanrun")
        # ② 鸿蒙特有消费者测试：ctest 注册用例 test_sems-opus，
        #    dlopen 插件 + 校验 amci_exports 导出契约 + 真实 encode/decode
        cmake = CMake(self)
        cmake.test()
