#!/usr/bin/env python3
"""Conan recipe — exprtk 0.0.2 (header-only; CMake toolchain only for upstream tests)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ExprtkConan(ConanFile):
    name = "exprtk"
    version = "0.0.2"
    description = "ExprTk - C++ Mathematical Expression Toolkit Library"
    license = "MIT"
    homepage = "https://github.com/ArashPartow/exprtk"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": False}
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if not self.options.run_upstream_tests:
            self.output.info(
                "Upstream tests skipped (run_upstream_tests=False). "
                "Enable with -o 'exprtk/*:run_upstream_tests=True'."
            )
            return
        # 上游测试：exprtk_test.cpp（自写框架，main() 顺序执行 run_test00..21，
        # 共 22 个测试函数，单一 numeric_type）。
        # 写源码目录的缘由：本环境 CMake 助手不支持 src_folder 参数，且上游
        # 0.0.2 根目录本无 CMakeLists.txt，无覆盖风险（no_copy_source 下为
        # conan 缓存副本，不污染归档）。
        # 数据文件必须复制到构建目录：run_test14 从进程 CWD 加载
        # exprtk_functional_test.txt / exprtk_functional_ext_test.txt，
        # 缺失时上游代码静默 return true（空转通过），故先复制再运行。
        copy(self, "exprtk_functional*_test.txt", self.source_folder, self.build_folder)
        with open(os.path.join(self.source_folder, "CMakeLists.txt"), "w") as f:
            f.write(
                "cmake_minimum_required(VERSION 3.15)\n"
                "project(exprtk_upstream_tests CXX)\n"
                "set(CMAKE_CXX_STANDARD 14)\n"
                "set(CMAKE_CXX_STANDARD_REQUIRED ON)\n"
                "add_executable(exprtk_test ${CMAKE_CURRENT_SOURCE_DIR}/exprtk_test.cpp)\n"
                "target_compile_options(exprtk_test PRIVATE -O0)\n"
            )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run(os.path.join(self.build_folder, "exprtk_test"))

    def package(self):
        copy(
            self,
            pattern="exprtk.hpp",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "exprtk")
        self.cpp_info.set_property("cmake_target_name", "exprtk::exprtk")
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
