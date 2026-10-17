#!/usr/bin/env python3
"""Conan recipe — oaknut 1.2.2-git20240301.94c726c (header-library).

oaknut 是 merryhime 的 C++20 AArch64 (ARMv8.0~8.3) 汇编器/代码发射器，header-only。
上游 CMakeLists.txt 用 `add_library(oaknut INTERFACE)` + `cxx_std_20`，install 只装
include/oaknut/*.hpp 与 cmake config（oaknutConfig.cmake + oaknutTargets.cmake），
无 .so/.a/.bin。

运行时依赖：无（纯 header-only）。
测试依赖：上游 `find_package(Catch2 3 REQUIRED)` + `<catch2/catch_test_macros.hpp>`，
本仓库仅有 catch2/2.13.10-r0（v2 API 与 v3 不兼容），故配方 BUILD_TESTING=OFF
跳过上游 Catch2 测试；改由 test_package 以 CodeGenerator/VectorCodeGenerator
指令编码断言做消费者验证（确定性、无 JIT、无 Catch2）。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get
from conan.tools.scm import Version


class OaknutConan(ConanFile):
    name = "oaknut"
    version = "1.2.2-git20240301.94c726c"
    description = "A C++20 assembler for AArch64 (ARMv8.0 to ARMv8.3)"
    license = "MIT"
    homepage = "https://github.com/merryhime/oaknut"
    url = ""  # CI fills this
    topics = ("aarch64", "arm64", "assembler", "jit", "header-only", "cpp20")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        # oaknut 是 C++20 header-only 库；共享 profile 为 cppstd=17，需强制 C++20。
        self.settings.compiler.cppstd = 20

    def validate(self):
        cppstd = self.settings.compiler.get_safe("cppstd")
        if cppstd and Version(str(cppstd)) < 20:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++20 or higher, but compiler.cppstd is {cppstd}."
            )
        compiler = str(self.settings.compiler)
        version = self.settings.compiler.version
        if compiler == "clang" and Version(str(version)) < "12":
            raise ConanInvalidConfiguration(
                f"{self.ref} requires clang >= 12 for C++20, got {compiler} {version}."
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，
        # 而 cmake 装的平台文件叫 OHOS（与 fmt/asmjit/mitama-cpp-result 一致）。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # C++20 显式声明（规避 E096：OHOS 上 CMake 编译特性检测失败）。
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_EXTENSIONS"] = "OFF"
        # Catch2 3 未发布，跳过上游测试（test_package 做消费者验证）。
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "oaknut")
        self.cpp_info.set_property("cmake_target_name", "merry::oaknut")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
