#!/usr/bin/env python3
"""Conan recipe — mINI 0.9.20（header-only C++ INI 读写库）.

上游 metayeti/mINI：单个头文件 src/mini/ini.h（781 行，C++17，零依赖，
无编译产物）。本配方不做任何源码改动，只做三件事：
  1) 把 src/mini/ini.h 装到 include/mini/ini.h，LICENSE 装到 licenses/；
  2) build() 里**真跑**上游自带测试套件（tests/ 下 9 个 test*.cpp，
     lest 单头测试框架，共 54 个 CASE 用例）——用上游自己的
     tests/CMakeLists.txt 编出 9 个测试可执行目标，再由 ctest 串行跑；
  3) 声明 CMake / pkg-config 消费者契约供下游 find_package / pkg-config 使用。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"

# CTest harness：直接复用上游 tests/CMakeLists.txt 的 9 个可执行目标
# （上游该文件只 add_executable、不注册 add_test），这里补 enable_testing()
# 与 add_test() 让 ctest 汇总，并把上游 run.sh 的 `-p`（打印每个用例）带上，
# 便于在 CI 日志里逐用例核对。
_CTEST_HARNESS = """cmake_minimum_required(VERSION 3.15)
project(mini_upstream_ctest CXX)

if(NOT DEFINED MINI_UPSTREAM_TESTS_DIR)
    message(FATAL_ERROR "MINI_UPSTREAM_TESTS_DIR is required (upstream tests/ dir)")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_testing()
add_subdirectory("${MINI_UPSTREAM_TESTS_DIR}" "${CMAKE_CURRENT_BINARY_DIR}/upstream_tests")

file(GLOB MINI_TEST_SOURCES "${MINI_UPSTREAM_TESTS_DIR}/test*.cpp")
foreach(_mini_src ${MINI_TEST_SOURCES})
    get_filename_component(_mini_name "${_mini_src}" NAME_WE)
    if(TARGET ${_mini_name})
        add_test(NAME ${_mini_name} COMMAND ${_mini_name} -p)
    endif()
endforeach()
"""


class MiniConan(ConanFile):
    name = "mini"
    version = "0.9.20"
    package_type = "header-library"
    description = ("mINI — tiny header-only C++ library for reading and writing "
                   "INI files (C++17, zero dependencies)")
    homepage = "https://github.com/metayeti/mINI"
    license = "MIT"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/m/mini/0.9.20"
    topics = ("ini", "configuration", "header-only", "cpp17")

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 tests/CMakeLists.txt 声明 cmake_minimum_required(3.5)；
        # 部分平台 CMake 已开始拒绝 <3.5 的兼容档，显式放行到 3.5。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        """唯一目的：真跑上游测试套件（header-only，本身无需编译）。"""
        if not can_run(self):
            self.output.warning(
                "cross-building profile: 上游 tests/ 的 9 个 lest 测试可执行文件"
                "无法在本机运行，已跳过（CI 的 ohos-aarch64 profile 为原生构建，"
                "会真实执行）")
            return
        harness_dir = os.path.join(self.build_folder, "ctest_harness")
        os.makedirs(harness_dir, exist_ok=True)
        with open(os.path.join(harness_dir, "CMakeLists.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write(_CTEST_HARNESS)
        upstream_tests = os.path.join(self.source_folder, "tests").replace("\\", "/")

        cmake = CMake(self)
        cmake.configure(build_script_folder=harness_dir,
                        cli_args=[f"-DMINI_UPSTREAM_TESTS_DIR={upstream_tests}"])
        cmake.build()

        # 上游测试真跑（与 test_package/MANIFEST.yml 的 upstream_check_command
        # 逐字一致）：ctest 串行跑 9 个可执行文件、-V 展开每个 lest 用例输出，
        # 任一用例失败即非零退出并让 conan create 失败。
        self.run("ctest --output-on-failure -V -j1", cwd=self.build_folder)

    def package(self):
        copy(self, "ini.h", src=os.path.join(self.source_folder, "src", "mini"),
             dst=os.path.join(self.package_folder, "include", "mini"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        # header-only：settings 组合不影响包内容
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        # header-only：不交付 bin/ 与 lib/
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # 消费者契约：find_package(mINI) -> mINI::mINI；pkg-config: mini
        self.cpp_info.set_property("cmake_file_name", "mINI")
        self.cpp_info.set_property("cmake_target_name", "mINI::mINI")
        self.cpp_info.set_property("pkg_config_name", "mini")
