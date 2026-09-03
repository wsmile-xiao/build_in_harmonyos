#!/usr/bin/env python3
"""Conan recipe — fast-cdr 2.3.5 (CMake, C++ library).

eProsima Fast-CDR is a C++ library for CDR serialization (used by FastDDS).
Build system is CMake, not autotools (init template was corrected accordingly).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class FastcdrConan(ConanFile):
    name = "fast-cdr"
    version = "2.3.5"
    description = "eProsima FastCDR: C++ library for CDR serialization"
    license = "Apache-2.0"
    homepage = "https://github.com/eProsima/Fast-CDR"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游测试套件（test/cdr、test/xcdr）通过 find_package(GTest CONFIG REQUIRED)
        # 链接 GTest::gtest_main；gtest/1.17.0 已在 ohpcd 发布（R02 启用的上游测试门禁）
        self.requires("gtest/1.17.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 启用上游测试（R02 门禁）：gtest/1.17.0 已由 requirements 注入，test/cdr、test/xcdr
        # 及 cmake.force_standard 模块测试随 BUILD_TESTING=ON 构建并注册 ctest。
        # BUILD_TESTING 必须以 -D 传入命令行：CMakeLists.txt 顶部 if(NOT BUILD_TESTING)
        # 在 project() 加载 toolchain 前求值，tc.variables 写入 toolchain 的 set(CACHE)
        # 会因顶层 FORCE OFF 已存在而不覆盖；configure(variables=...) 直接进命令行参数。
        # 禁用上游文档：文档需要 doxygen/wget
        tc.variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.variables["CHECK_DOCUMENTATION"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # gtest 1.17.0 配方 package_info 只声明单个 gtest::gtest target，但上游
        # test/cdr、test/xcdr 链接 GTest::gtest_main；gtest 包内自带官方
        # GTestConfig.cmake（GTest::gtest/gtest_main/gmock/gmock_main 完整 targets，
        # 指向包内 libgtest.a/libgtest_main.a）。将 GTest_DIR 指向该官方 config，
        # 使 find_package(GTest CONFIG REQUIRED) 命中完整 targets（CMakeDeps 的
        # gtest-config.cmake 只含 gtest::gtest，会缺 GTest::gtest_main）。
        gtest_pkg = self.dependencies["gtest"].package_folder
        if gtest_pkg:
            tc.variables["GTest_DIR"] = os.path.join(gtest_pkg, "lib", "cmake", "GTest")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # BUILD_TESTING 经 configure(variables=...) 以 -D 传入命令行，使 CMakeLists.txt
        # 顶部 if(NOT BUILD_TESTING) 在 project() 前即见 ON（toolchain set(CACHE) 会被
        # 顶层 FORCE OFF 覆盖，无法生效）；BUILD_TESTING=ON 构建上游 test/cdr、test/xcdr
        # 与 cmake.force_standard 模块测试。
        cmake.configure(variables={"BUILD_TESTING": "ON"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["fastcdr"]
        self.cpp_info.set_property("cmake_file_name", "fastcdr")
        self.cpp_info.set_property("cmake_target_name", "fastcdr::fastcdr")
