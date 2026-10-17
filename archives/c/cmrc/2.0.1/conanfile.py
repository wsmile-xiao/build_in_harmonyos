#!/usr/bin/env python3
"""Conan recipe — cmrc 2.0.1 (CMakeRC: standalone CMake-based C++ resource compiler).

cmrc 不是传统「库+头」分发：上游只发布一个 CMake 模块 CMakeRC.cmake。
消费者 include(CMakeRC.cmake) 后调用 cmrc_add_resource_library()，
cmrc 在 configure/build 期生成 cmrc.hpp 与资源静态库（含嵌入式二进制数据）。
因此本包按 ecbuild 同款「CMake 模块包」模型打包：
  - 把 CMakeRC.cmake 安装到 lib/cmake/cmrc/（G4 产物门禁经 lib/ 通过）
  - 用 cmake_build_modules 让 CMakeDeps 生成的 config 主动 include 该模块，
    下游 find_package(cmrc) 后即可直接使用 cmrc_add_resource_library 与 cmrc::base。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout

import os


class CmrcConan(ConanFile):
    name = "cmrc"
    version = "2.0.1"
    description = "CMakeRC - A Standalone CMake-Based C++ Resource Compiler"
    license = "MIT"
    homepage = "https://github.com/vector-of-bool/cmrc"
    url = "https://github.com/vector-of-bool/cmrc"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无编译产物：cmrc 只有 CMake 模块（CMakeRC.cmake），构建期无源码可编。
        # 若 conandata 声明补丁，在此应用。
        apply_conandata_patches(self)

    def package(self):
        # CMake 模块 + 许可证（dst 必须为绝对路径，相对路径会被解析到 build 目录）
        copy(self, "CMakeRC.cmake",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "cmake", "cmrc"))
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 纯模块分发：无 os/compiler 相关二进制，单一 package_id
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []

        # 模块文件目录：下游可显式 list(APPEND CMAKE_MODULE_PATH ...) + include(CMakeRC.cmake)
        self.cpp_info.builddirs = ["lib/cmake/cmrc"]

        # cmake_build_modules 让 CMakeDeps 生成的 cmrc-config.cmake 自动
        # include 上游 CMakeRC.cmake，把 cmrc_add_resource_library/cmrc::base
        # 注入下游作用域（与 ecbuild 同款机制）。
        self.cpp_info.set_property("cmake_build_modules",
                                   ["lib/cmake/cmrc/CMakeRC.cmake"])
        self.cpp_info.set_property("cmake_file_name", "cmrc")