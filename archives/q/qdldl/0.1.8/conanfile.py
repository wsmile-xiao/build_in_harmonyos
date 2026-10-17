#!/usr/bin/env python3
"""Conan recipe for qdldl 0.1.8 — CMake project.

qdldl (OSQP) 为纯 C、自包含 CMake 库，无第三方依赖。
上游选项 QDLDL_BUILD_STATIC_LIB / QDLDL_BUILD_SHARED_LIB 分别控制
静态库与共享库；此处映射到 Conan 标准 shared 选项。
头文件安装在 include/qdldl/ 子目录，消费方使用 #include <qdldl/qdldl.h>。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QdldlConan(ConanFile):
    name = "qdldl"
    version = "0.1.8"
    description = "QDLDL: a free LDL^T factorisation routine for symmetric quasi-definite matrices (part of OSQP)"
    license = "Apache-2.0"
    homepage = "https://github.com/osqp/qdldl"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 映射 Conan shared 选项到上游 QDLDL 构建开关（库类型，非系统同名库）
        tc.variables["QDLDL_BUILD_STATIC_LIB"] = "OFF" if self.options.shared else "ON"
        tc.variables["QDLDL_BUILD_SHARED_LIB"] = "ON" if self.options.shared else "OFF"
        # 配方构建不编译 demo/单测（单测在探索阶段独立执行并登记于 MANIFEST.yml）
        tc.variables["QDLDL_BUILD_DEMO_EXE"] = "OFF"
        tc.variables["QDLDL_UNITTESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["qdldl"]
        self.cpp_info.set_property("cmake_file_name", "qdldl")
        self.cpp_info.set_property("cmake_target_name", "qdldl::qdldl")
