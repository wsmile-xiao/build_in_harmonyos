#!/usr/bin/env python3
"""Conan recipe for libmsym 0.2.3 — CMake build system.

上游为 C99 库（无外部依赖，仅链系统 libm）。CMAKE_POLICY_VERSION_MINIMUM 为
CMake 4.x 必需的兼容开关（上游 cmake_minimum_required(VERSION 2.8.11)）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibmsymConan(ConanFile):
    name = "libmsym"
    version = "0.2.3"
    description = "C library dealing with point group symmetry in molecules"
    license = "MIT"
    homepage = "https://github.com/mcodev31/libmsym"
    url = "https://github.com/mcodev31/libmsym/archive/refs/tags/v0.2.3.tar.gz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # examples 默认 OFF；显式声明交付面（CLI 不安装，只用库）
        tc.cache_variables["MSYM_BUILD_EXAMPLES"] = "OFF"
        if self.settings.os == "OHOS":
            # HarmonyOS 在 CMake 中没有 Platform/HarmonyOS.cmake：Linux 平台模块设置的
            # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空，于是即使上游设了 VERSION/SOVERSION，
            # shared 变体的 .so 也没有 DT_SONAME（下游链接器无法按 SONAME 寻址）。显式补成
            # 未版本化、可重定位的 SONAME（与仓库内已适配包的既有做法一致，见 E383）。
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM 必须在 configure 命令行上给：上游
        # cmake_minimum_required(VERSION 2.8.11) 的首行策略检查发生在 CMakeToolchain
        # 加载之前，写在 toolchain 文件里的同名变量不可达（CMake 4.x 直接报
        # "Compatibility with CMake < 3.5 has been removed"）。
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["msym"]
        # 上游 CMakeLists 在 UNIX 下显式 target_link_libraries(msym m)
        self.cpp_info.system_libs = ["m"]
