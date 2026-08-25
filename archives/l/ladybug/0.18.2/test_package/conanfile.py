#!/usr/bin/env python3
"""Conan test_package — ladybug 0.18.2 (Conan L1 official test).

R34: 实质调用被测包 —— 编译并运行 C API 测试程序（创建内存图库、建表、
写入节点、查询校验），同时 smoke test 运行 lbug CLI 二进制。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LadybugTestConan(ConanFile):
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
        # 1) R34: 运行 C API 实质测试程序（建库/建表/写节点/MATCH 查询校验）
        self.run(os.path.join(self.cpp.build.bindir, "test_ladybug"), env="conanrun")
        # 2) 运行 AI 补充上游测试用例（规则 4：覆盖 value/data_type/query_result/
        #    prepared_statement/聚合/DDL/DML/过滤/事务/版本 10 大场景，58 断言）
        self.run(os.path.join(self.cpp.build.bindir, "test_ai"), env="conanrun")
        # 3) smoke: lbug CLI 二进制
        lbug_bin = os.path.join(self.dependencies["ladybug"].package_folder, "bin", "lbug")
        if os.path.exists(lbug_bin):
            self.run(f'"{lbug_bin}" --version', env="conanrun")
        else:
            self.output.warning("lbug CLI not found in package bin/")
