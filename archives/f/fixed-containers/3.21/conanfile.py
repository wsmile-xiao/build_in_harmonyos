#!/usr/bin/env python3
"""Conan recipe — fixed-containers 3.21 (CMake header-only C++20 library).

fixed-containers 是 Tesla 维护的现代 C++20 无堆分配固定容器库
（fixed_vector / fixed_map / fixed_string / enum_map 等），
CMake INTERFACE 库，仅含头文件，无编译产物。依赖 magic_enum（header-only）。
上游官方源：https://github.com/teslamotors/fixed-containers （无 release tag，取 main 分支）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

import os


class FixedContainersConan(ConanFile):
    name = "fixed-containers"
    version = "3.21"
    description = "C++20 header-only library of fixed-capacity containers without heap allocation"
    license = "MIT"
    homepage = "https://github.com/teslamotors/fixed-containers"
    url = ""  # CI fills this
    topics = ("containers", "header-only", "fixed-capacity", "cpp20", "no-heap")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("magic_enum/0.9.7")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMakeLists：PROJECT_IS_TOP_LEVEL 时默认开 BUILD_TESTS，
        # 配方内只构建/安装 INTERFACE 库本身；上游测试在适配验证阶段单独运行（R51）。
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["FIXED_CONTAINERS_OPT_INSTALL"] = "ON"
        # 上游要求 C++20（CMAKE_CXX_STANDARD 20）
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 上游 install(EXPORT ... NAMESPACE fixed_containers::) 生成
        # fixed_containersConfig.cmake，target = fixed_containers::fixed_containers
        self.cpp_info.set_property("cmake_file_name", "fixed_containers")
        self.cpp_info.set_property("cmake_target_name", "fixed_containers::fixed_containers")
        self.cpp_info.requires = ["magic_enum::magic_enum"]
        self.cpp_info.libs = []
