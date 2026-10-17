#!/usr/bin/env python3
"""Conan recipe — OpenJPH (HTJ2K / JPEG2000 Part-15 codec, CMake).

OpenJPH is an open-source implementation of High-Throughput JPEG2000 (HTJ2K),
also known as JPH / JPEG2000 Part-15 (ISO/IEC 15444-15 / ITU-T T.814).
Build system: CMake (C/C++).
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenjphConan(ConanFile):
    name = "openjph"
    version = "0.31.0"
    description = "Open-source implementation of JPEG2000 Part-15 (HTJ2K / JPH)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/aous72/OpenJPH"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        # 上游 gtest 套件（tests/，86 用例）需要 googletest。使用制品仓已发布的
        # gtest 包，替换上游 tests/CMakeLists.txt 的 FetchContent 联网下载。
        self.test_requires("gtest/1.17.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游测试码流随配方下载（commit 固定），供 tests/ 的 gtest 套件读取。
        get(self, **self.conan_data["test_codestreams"],
            destination="test_codestreams", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 裁剪外部依赖：TIFF 支持关闭（PPM/YUV I/O 不受影响）。
        # 注：0.31.0 上游已无 TBB 依赖（grep 全树无命中），无需裁剪动作。
        tc.variables["OJPH_ENABLE_TIFF_SUPPORT"] = "OFF"
        # 上游测试套件（tests/，86 个 gtest 用例）纳入构建，并在 build() 中执行；
        # googletest 与测试码流均由本配方提供，构建期无 FetchContent 联网下载。
        tc.variables["OJPH_BUILD_TESTS"] = "ON"
        tc.variables["OJPH_TEST_CODESTREAMS_DIR"] = os.path.join(
            self.source_folder, "test_codestreams").replace("\\", "/")
        # 指向 Conan gtest 包内的上游 GTestConfig.cmake（提供 GTest::gtest_main）
        gtest = self.dependencies["gtest"]
        tc.variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest").replace("\\", "/")
        tc.variables["OJPH_BUILD_EXECUTABLES"] = "ON"
        # Fix SONAME on HarmonyOS (CMake doesn't recognize OHOS platform)
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # RPATH for installed binaries
        tc.variables["CMAKE_SKIP_RPATH"] = "OFF"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游官方测试套件（tests/ ctest：test_executables 85 + test_mixed_coc 1）；
        # 失败即 conan create 失败 → 构建失败。本库为 native 适配（构建平台与
        # 目标平台一致），测试二进制可直接执行，故无条件运行。
        # OHOS 上 CMake 不写 build tree 的 RPATH，测试进程（及其 popen 出的
        # ojph_expand/ojph_compress）需要显式提供 libopenjph.so 搜索路径。
        env = Environment()
        env.append_path("LD_LIBRARY_PATH",
                        os.path.join(self.build_folder, "src", "core"))
        with env.vars(self).apply():
            cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openjph"]
        self.cpp_info.set_property("cmake_file_name", "openjph")
        self.cpp_info.set_property("cmake_target_name", "openjph")
        self.cpp_info.set_property("pkg_config_name", "openjph")
        self.cpp_info.includedirs = ["include"]
