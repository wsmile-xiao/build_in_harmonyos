#!/usr/bin/env python3
"""Conan recipe for ctpg 1.3.7 — C++ Compile Time Parser Generator (header-only).

ctpg 是 C++17 单头文件（include/ctpg/ctpg.hpp）编译期 LR(1) 解析器生成库。
header-only（CMake INTERFACE library），运行期零依赖；上游测试用 Catch2 2.x
（find_package(Catch2 2 REQUIRED)），由 ohpcd 已发布的 catch2/2.13.10-r0 提供。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CtpgConan(ConanFile):
    name = "ctpg"
    version = "1.3.7"
    description = "Compile Time Parser Generator — a single header library turning C++ code into LR(1) parser in compile time"
    license = "MIT"
    homepage = "https://github.com/peter-winter/ctpg"
    url = ""  # CI fills this
    topics = ("parser", "lalr", "compile-time", "header-only", "cpp17")

    settings = "os", "compiler", "build_type", "arch"

    generators = "CMakeDeps"

    def requirements(self):
        # catch2：仅上游测试（tests/ 用 Catch2 2.x——CTPG_ENABLE_TESTS）需要，
        # 且只在可运行本机测试的构建（非纯交叉打包）时引入
        if can_run(self):
            self.requires("catch2/2.13.10-r0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: os 判定必须覆盖 OHOS（OHOS 适配版 conan 已把 OHOS 映射到
        # CMAKE_SYSTEM_NAME=HarmonyOS，此处无需手动设 system_name）
        tc.variables["CTPG_ENABLE_INSTALL"] = "ON"
        tc.variables["CTPG_WARNING_FLAGS"] = "OFF"
        if can_run(self):
            tc.variables["CTPG_ENABLE_TESTS"] = "ON"
            # 上游 CMakeLists 调用 include(Catch)/catch_discover_tests（Catch2 2.x
            # 的 CTest 集成模块）。ohpcd 的 catch2/2.13.10-r0 只打包头文件不含该
            # 模块——注入最小 Catch.cmake（把 testbin 注册为单个 ctest 用例，
            # 运行即执行全部 52 个 TEST_CASE），不改上游源码。
            mod_dir = os.path.join(self.build_folder, "cmake-modules")
            os.makedirs(mod_dir, exist_ok=True)
            with open(os.path.join(mod_dir, "Catch.cmake"), "w") as f:
                f.write(
                    "# Minimal Catch.cmake for ctpg upstream ctest integration\n"
                    "function(catch_discover_tests TARGET)\n"
                    "    add_test(NAME ${TARGET} COMMAND ${TARGET})\n"
                    "endfunction()\n"
                )
            tc.variables["CMAKE_MODULE_PATH"] = mod_dir
        else:
            tc.variables["CTPG_ENABLE_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        # header-only——无需编译库本身；CTPG_ENABLE_TESTS=ON 时构建并运行上游
        # testbin（16 个 tests/*.cpp + main.cpp，Catch2 注册 52 个用例）
        if not can_run(self):
            return
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ctpg")
        self.cpp_info.set_property("cmake_target_name", "ctpg::ctpg")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
