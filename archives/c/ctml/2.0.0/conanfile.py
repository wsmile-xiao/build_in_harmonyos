#!/usr/bin/env python3
"""Conan recipe — ctml 2.0.0 (header-only, CMake).

CTML (github.com/tinfoilboy/CTML) 是纯头文件 C++11 HTML 文档构造库：
交付物为单头 `include/ctml.hpp`（1542 行），0 外部依赖（W0 实查：配方
requires/tool_requires 双零，上游 CMakeLists 只有 INTERFACE 目标、无任何
find_package/target_link_libraries 外部库）。

上游带 CMakeLists.txt 并内置测试（CTML_TESTS_ENABLE 默认 ON →
tests/behavior_tests.cpp + tests/construction_tests.cpp → 可执行 CTMLTest →
add_test(NAME CTMLTests)），故按 docs/TEST_QUALITY_SPEC.md §3.1（层 1 必做）
在 build() 里 configure + build + cmake.test()（ctest）实跑上游官方测试，
test_package/MANIFEST.yml 的 upstream_test_in_build 因此为 true。

平台适配点（唯一，零补丁）：
  上游 `cmake_minimum_required(VERSION 3.0)`，设备/CI 的 CMake 4.x 已移除
  <3.5 兼容（"Compatibility with CMake < 3.5 has been removed"，configure 必炸）。
  处置 = 传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4 官方提示的逃生开关；
  CMake 3.x 下只是未使用变量告警），不改上游源码、不打补丁。
"""
import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CtmlConan(ConanFile):
    name = "ctml"
    version = "2.0.0"
    description = "CTML — a C++ HTML document constructor, header-only, standard library only"
    license = "MIT"
    homepage = "https://github.com/tinfoilboy/CTML"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("html", "header-only", "cpp11", "generator")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-2 实查：0 运行依赖（conan list ctml/* -r=ohpcd 与本配方 requires 双零）
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # 上游 CMakeLists: set(CMAKE_CXX_STANDARD 11)，README 标注 C++11
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游测试树默认开启（CTML_TESTS_ENABLE=ON），层 1 上游测试在 build() 实跑
        tc.cache_variables["CTML_TESTS_ENABLE"] = True
        # CMake 4.x 移除 cmake_minimum_required(VERSION 3.0) 的兼容性
        # （上游写死 3.0，源码一字不改），见文件头「平台适配点」
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 层 1：上游官方测试（R51 三步法）──
        # enable_testing() + add_test(NAME CTMLTests) 由上游 CMakeLists 提供，
        # ctest 运行 CTMLTest（Catch2 v2 单头，behavior + construction 两组），
        # 任一断言失败 → ctest rc != 0 → conan create 失败（非空跑、非 BUILD_TESTING=OFF 造假）
        cmake.test()

    def package(self):
        copy(
            self,
            "ctml.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "CTML")
        self.cpp_info.set_property("cmake_target_name", "CTML::CTML")
