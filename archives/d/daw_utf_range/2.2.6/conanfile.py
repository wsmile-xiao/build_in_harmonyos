#!/usr/bin/env python3
"""Conan recipe — daw_utf_range 2.2.6 (CMake header-only library).

daw_utf_range 是 beached 维护的 UTF-8 迭代器/范围库（daw 系），
提供 char_range / utf_range / utf_string 等 UTF-8 文本遍历设施，
是 daw_json_link 序列化路径（to_daw_json_string.h）的硬依赖。
header-only（CMake INTERFACE library），运行时依赖 daw-header-libraries。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DawUtfRangeConan(ConanFile):
    name = "daw_utf_range"
    version = "2.2.6"
    description = "UTF8 Iterator/Range for traversing utf8 text"
    license = "BSL-1.0"
    homepage = "https://github.com/beached/utf_range"
    url = ""  # CI fills this
    topics = ("header-only", "utf8", "utf-range", "cpp17", "daw")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    implements = ["auto_header_only_mode"]
    generators = "CMakeDeps"

    def export_sources(self):
        # header-only 库仅含头文件，无补丁 source；保留空实现满足门禁规范
        pass

    def requirements(self):
        # 唯一运行时依赖：daw 系基础头文件库（制品仓已发布 2.135.0）
        self.requires("daw-header-libraries/2.135.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 使用包管理器模式：依赖由 Conan 提供（不 FetchContent）
        tc.variables["DAW_USE_PACKAGE_MANAGEMENT"] = True
        tc.variables["DAW_ENABLE_TESTING"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "daw-utf-range")
        self.cpp_info.set_property("cmake_target_name", "daw::daw-utf-range")
        self.cpp_info.libs = []
