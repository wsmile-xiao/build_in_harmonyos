#!/usr/bin/env python3
"""Conan recipe — daw_json_link 3.38.1 (CMake header-only library).

daw_json_link 是 beached 维护的静态 JSON 解析/序列化 C++17 库（daw 系），
通过数据契约（daw::json::json_data_contract）实现零运行时反射的
编译期绑定：from_json / to_json / json_link 系列设施。
header-only（CMake INTERFACE library），运行时依赖 daw-header-libraries
与 daw-utf-range（序列化路径）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DawJsonLinkConan(ConanFile):
    name = "daw_json_link"
    version = "3.38.1"
    description = "Static JSON parsing in C++ with data contract based binding"
    license = "BSL-1.0"
    homepage = "https://github.com/beached/daw_json_link"
    url = ""  # CI fills this
    topics = ("header-only", "json", "json-parsing", "serialization", "cpp17", "daw")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    implements = ["auto_header_only_mode"]
    generators = "CMakeDeps"

    def export_sources(self):
        # header-only 库仅含头文件，无补丁 source；保留空实现满足门禁规范
        pass

    def requirements(self):
        # daw 系依赖（两者制品仓已发布；CMake INTERFACE 链接链）
        self.requires("daw-header-libraries/2.135.0")
        self.requires("daw-utf-range/2.2.6")

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
        # 关闭上游测试与可选 vc（version check）目标
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
        self.cpp_info.set_property("cmake_file_name", "daw-json-link")
        self.cpp_info.set_property("cmake_target_name", "daw::daw-json-link")
        self.cpp_info.libs = []
