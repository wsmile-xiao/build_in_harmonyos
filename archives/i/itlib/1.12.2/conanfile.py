#!/usr/bin/env python3
"""Conan recipe — itlib 1.12.2 (CMake, header-only).

itlib (iboB's Template Libraries) 是一组与 C++ 标准库相似或扩展的
小型单头文件模板库集合（any/flat_map/flat_set/small_vector/span/expected
等 35 个头文件）。上游构建系统为 CMake，以 INTERFACE（header-only）目标
itlib::itlib 提供头文件，install 规则安装 include/itlib/*.hpp 并导出
CMake package config。无编译计划、无运行时依赖，仅依赖标准库。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ItlibConan(ConanFile):
    name = "itlib"
    version = "1.12.2"
    description = "iboB's Template Libraries — 一组与 C++ 标准库相似或扩展的小型单头文件 C++ 模板库集合"
    license = "MIT"
    homepage = "https://github.com/iboB/itlib"
    url = "https://github.com/iboB/itlib"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

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
        if self.settings.os == "OHOS":
            # 纯头文件库，无编译产物；保持 Linux 语义。CMake INTERFACE 目标仅
            # 依赖标准库，无需 OHOS 平台特化。
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 上游测试经 CPM 从 GitHub 拉取 doctest/icm/doctest-util/picobench
        # （E342：离线 CI 下 configure 期网络 bootstrap 不可控），且头文件库
        # 无编译产物；消费者验证由 test_package 承担（R34 实质调用公开头文件
        # API）。上游测试在本地单独枚举并运行（见 reports/upstream-test-ledger.md），
        # 故关闭 ITLIB_BUILD_TESTS，避免 conan create 时 CPM 下载失败。
        tc.variables["ITLIB_BUILD_TESTS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []