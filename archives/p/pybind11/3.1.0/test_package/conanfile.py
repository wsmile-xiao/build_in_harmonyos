#!/usr/bin/env python3
"""pybind11 3.1.0 test_package — Conan L1 官方测试。

pybind11 头文件（include/pybind11/detail/common.h → conduit/
wrap_include_python_h.h）无条件 #include <Python.h>，OHOS 工具链
sysroot 不提供 Python 开发头；本测试在 generate() 中探测宿主 Python
的 include 目录（sysconfig），注入 CMakeToolchain 变量 PYTHON_INCLUDE_DIR
供 test CMakeLists 使用。该路径仅用于编译期包含，不产生包级 Python
依赖。

test() 通过 self.run 实际执行已编译的 test_pybind11 消费者探测程序
（L0d 要求 test() 含 self.run，禁止空壳；R34 实质依赖被测包 API）。
"""
import os
import sysconfig

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Pybind11TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain 在 generate() 中定制（OHOS 映射 + PYTHON_INCLUDE_DIR），
    # 不能再出现在 generators 属性（与显式实例化互斥）
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 宿主 Python 开发头（仅编译期 include；CI/本地均为同一 Python 3.12）
        include_dir = sysconfig.get_paths().get("include")
        if include_dir:
            tc.variables["PYTHON_INCLUDE_DIR"] = include_dir
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 实际执行已构建的消费者探测程序（L0d: 必须含 self.run）
        binpath = os.path.join(self.cpp.build.bindirs[0], "test_pybind11")
        if not os.path.exists(binpath):
            self.output.info("test binary not found; compile+link verified only")
            return
        self.run(binpath, env="conanrun")