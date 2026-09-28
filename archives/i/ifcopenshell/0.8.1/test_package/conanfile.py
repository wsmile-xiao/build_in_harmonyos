#!/usr/bin/env python3
"""Conan test_package — L1 consumer test for ifcopenshell.

Must substantively exercise the built library (R34): parse a minimal IFC
STEP file using the installed IfcParse API.

ohpcd 的 boost/eigen 等依赖包的 CMakeDeps 元数据缺少 include 路径，
此处显式声明依赖并把依赖 include 目录注入 toolchain，供 CMakeLists 使用。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class IfcopenshellTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain 在 generate() 中手动实例化以注入依赖 include 变量，此处只声明 CMakeDeps
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 公共头文件依赖（ifcopenshell 透传不全时 test_package 显式声明）
        self.requires("boost/1.90.0.4")
        self.requires("eigen/3.4.0")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")
        self.requires("opencascade/7.9.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 显式注入依赖 include 目录（绕开依赖包 CMakeDeps 元数据缺 include 的问题）
        for dep_name in ("boost", "eigen", "libxml2", "zlib", "opencascade"):
            dep = self.dependencies[dep_name]
            if dep.cpp_info.includedirs:
                tc.variables[f"{dep_name.upper()}_INCLUDE_DIR"] = os.path.join(
                    dep.package_folder, *dep.cpp_info.includedirs[0:1]
                )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d 要求 test() 通过 self.run() 实际执行被测二进制（R34 实质测试）
        cmake = CMake(self)
        cmake.test()
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ifcopenshell")
        self.run(test_bin, env="conanrun")
