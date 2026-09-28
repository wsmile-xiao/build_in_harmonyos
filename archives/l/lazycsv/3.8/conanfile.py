#!/usr/bin/env python3
"""Conan recipe — lazycsv 3.8 (header-only INTERFACE library).

lazycsv 是 C++17 单头文件 CSV 惰性解析库（无内存分配于构造/解析期）。
项目为 CMake INTERFACE 头文件库（project lazycsv VERSION 1.2.0，
cmake_minimum_required(VERSION 3.8...3.20)；任务版本 3.8 由此而来），
无编译产物、无 CLI、无外部依赖。

OHOS notes:
- 上游无 git tag（GitHub API/jsdelivr tags 均空，v3.8 等 codeload 全 404），
  官方源固定到 master 提交 6c36a9d66be1e652b0c06d4e34fb053b93caf0ff 的
  官方 commit 归档（SHA-256=19bc1673d9a60b82ed71f3ae8cfaa36105c15d6f6f2dfa496ca8d2386f9c573f）。
- 配方 build 关闭 BUILD_TESTING（上游 14 个 doctest TEST_CASE 在适配阶段
  独立构建运行并如实计入双口径台账，不在配方内重复打包）。
- 仅安装 include/lazycsv.hpp；cpp_info.libs 为空（header-only）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LazycsvConan(ConanFile):
    name = "lazycsv"
    version = "3.8"
    description = "lazycsv is a fast, lightweight and single-header C++ CSV parser library"
    license = "MIT"
    homepage = "https://github.com/ashtum/lazycsv"
    url = ""  # CI fills this
    topics = ("csv", "parser", "header-only", "cpp17", "lazy")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 适配版 conan 自动将 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，
        # 无需手动设置 system_name/triplet。配方 build 仅安装头文件，关闭上游测试
        # （上游 14 用例已在适配阶段独立构建运行并计入双口径台账）。
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_id(self):
        self.info.clear()  # 无构建产物，单一 package_id（header-only）

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "lazycsv")
        self.cpp_info.set_property("cmake_target_name", "lazycsv::lazycsv")
