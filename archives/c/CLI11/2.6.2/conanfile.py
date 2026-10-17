#!/usr/bin/env python3
"""Conan recipe — CLI11 2.6.2 (CMake header-only library).

CLI11 是一个 C++ 命令行解析库，header-only（INTERFACE library）。
仅需 CMake 配置安装头文件和 CMake 配置文件，无二进制编译。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Cli11Conan(ConanFile):
    name = "cli11"
    version = "2.6.2"
    description = "A command line parser for C++11 and beyond"
    license = "BSD-3-Clause"
    homepage = "https://github.com/CLIUtils/CLI11"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "CLI11 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库，所有 settings 组合产出相同的包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 注入 Catch2 v2.13.10 单头文件到 tests/catch2/catch.hpp，规避上游
        # tests/CMakeLists.txt 用 file(DOWNLOAD) 在网络受限环境失败的问题。
        # 放到 tests/catch2/ 子目录，避免覆盖上游 tests/catch.hpp 包装器。
        # 补丁 0001-use-local-catch2.patch 同时改写 tests/catch.hpp 包装器
        # 和 tests/CMakeLists.txt，让它们从本地 tests/catch2/catch.hpp 读取。
        catch2 = self.conan_data.get("catch2") or {}
        if not catch2:
            raise ConanInvalidConfiguration("conandata.yml 缺少 catch2 段")
        catch2_dir = os.path.join(self.source_folder, "tests", "catch2")
        os.makedirs(catch2_dir, exist_ok=True)
        dst_catch = os.path.join(catch2_dir, "catch.hpp")
        download(
            self,
            catch2["url"],
            "catch.hpp",
            sha256=catch2["sha256"],
        )
        # download() 落到 self.source_folder/catch.hpp，移动到 tests/catch2/catch.hpp
        src_catch = os.path.join(self.source_folder, "catch.hpp")
        if os.path.exists(src_catch):
            os.replace(src_catch, dst_catch)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["CMAKE_CXX_STANDARD"] = 11
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["BUILD_TESTING"] = True
        tc.variables["CLI11_BUILD_TESTS"] = True
        tc.variables["CLI11_BUILD_EXAMPLES"] = False
        tc.variables["CLI11_BUILD_DOCS"] = False
        tc.variables["CLI11_INSTALL"] = True
        tc.variables["CLI11_SINGLE_FILE"] = False
        tc.variables["CLI11_PRECOMPILED"] = False
        tc.variables["CLI11_MODULES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CLI11")
        self.cpp_info.set_property("cmake_target_name", "CLI11::CLI11")
        self.cpp_info.libs = []
