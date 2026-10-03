#!/usr/bin/env python3
"""Conan recipe — nanodbc 2.14.0 (CMake)"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class NanodbcConan(ConanFile):
    name = "nanodbc"
    version = "2.14.0"
    description = "A small C++ wrapper library for the native C ODBC API"
    license = "MIT"
    homepage = "https://github.com/nanodbc/nanodbc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("unixodbc/2.3.12")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 库本体：禁示例与上游测试（上游测试真跑在源码树独立构建中完成，
        # 证据归档于 notes.md 与 PR 统计表；test_package 跑消费者冒烟测试）
        tc.variables["NANODBC_DISABLE_EXAMPLES"] = True
        tc.variables["NANODBC_DISABLE_TESTS"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # ODBC 驱动管理器来自 Conan 包 unixodbc/2.3.12。
        # 上游 CMakeLists 的探测链（odbc_config 程序 / find_path uodbc_stats.h /
        # iodbc-config）均为宿主专用探测，交叉构建（OHOS）下必然全部落空并
        # FATAL_ERROR；0001 patch 在探测链之前插入显式路径分支，以下两个
        # cache 变量即该分支的输入。
        dep = self.dependencies["unixodbc"]
        tc.variables["ODBC_INCLUDE_DIR"] = os.path.join(dep.package_folder, "include")
        tc.variables["ODBC_LIBRARY"] = self._odbc_library(dep)
        tc.generate()

    @staticmethod
    def _odbc_library(dep):
        for libdir in dep.cpp_info.libdirs:
            for name in ("libodbc.so", "libodbc.a"):
                candidate = os.path.join(libdir, name)
                if os.path.exists(candidate):
                    return candidate
        raise RuntimeError("unixodbc package provides no libodbc library")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["nanodbc"]
        self.cpp_info.set_property("cmake_file_name", "nanodbc")
        self.cpp_info.set_property("cmake_target_name", "nanodbc::nanodbc")
