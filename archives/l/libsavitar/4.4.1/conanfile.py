#!/usr/bin/env python3
"""Conan recipe — libsavitar 4.4.1 (CMake, bundled pugixml).

libSavitar 是 Ultimaker 的 C++ 3MF 解析库。pugixml 以内嵌子目录
(add_subdirectory(pugixml)) 方式随源码分发，链接进 libSavitar.so，
不额外声明 requires。SIP Python 绑定(BUILD_PYTHON)与 GTest 测试
(BUILD_TESTS)在 OHOS 适配中关闭，测试由 test_package 消费者验证承担。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, collect_libs, apply_conandata_patches, export_conandata_patches, copy


class LibsavitarConan(ConanFile):
    name = "libsavitar"
    version = "4.4.1"
    description = "libSavitar is a C++ implementation of 3MF loading (Ultimaker)"
    license = "LGPL-3.0"
    homepage = "https://github.com/Ultimaker/libSavitar"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游默认会构建 SIP Python 绑定(依赖 Python3/SIP)与 GTest 测试，
        # OHOS 上关闭；库本体与捆绑的 pugixml 不受影响。
        tc.variables["BUILD_PYTHON"] = "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        # 上游用 BUILD_STATIC 控制静态库，映射 conan shared 选项。
        tc.variables["BUILD_STATIC"] = "ON" if not self.options.shared else "OFF"
        # 注意：Conan toolchain 会按 shared 选项强制 BUILD_SHARED_LIBS，
        # 因此 pugixml 必须静态由补丁 patches/0001-pugixml-static.patch 保证。
        # CMake 4.x 对 cmake_minimum_required(3.6) 的策略兼容。
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS 平台 CMake 不识别（unknown to cmake），共享库默认不带
        # SONAME 链接标志，导致 libSavitar.so 无 DT_SONAME（L5a）且
        # 导出 .cmake 含 IMPORTED_NO_SONAME TRUE（L5c）。显式补齐
        # SONAME 标志（与 adwaita-qt 同范式）。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        # 上游 Savitar 头文件用相对 include "../pugixml/src/pugixml.hpp"，
        # 安装后该相对路径对应 include/pugixml/src/，需要一并放置 pugixml
        # 公共头（pugiconfig.hpp 是 pugixml.hpp 同目录相对包含）才能被消费者解析。
        copy(self, "pugixml.hpp", src=os.path.join(self.source_folder, "pugixml", "src"),
             dst=os.path.join(self.package_folder, "include", "pugixml", "src"))
        copy(self, "pugiconfig.hpp", src=os.path.join(self.source_folder, "pugixml", "src"),
             dst=os.path.join(self.package_folder, "include", "pugixml", "src"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "Savitar")
        self.cpp_info.set_property("cmake_target_name", "Savitar::Savitar")
        # 头文件安装到 include/Savitar/（含生成的头 SavitarExport.h）