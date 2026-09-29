#!/usr/bin/env python3
"""Conan recipe — mdspan 0.6.0 (header-only C++ 标准提案 P0009 参考实现).

mdspan 是 C++ 标准库多维数组视图提案 P0009/P02640/P0009R9 的参考实现
（Kokkos 团队维护），交付物只有 `include/experimental/**` 21 个头文件，
上游 CMake 目标是 `INTERFACE`（`add_library(mdspan INTERFACE)`），无编译产物、
零依赖（`requires`/`tool_requires` 均为空）。

OHOS 适配要点（详见 notes.md）：

  * header-only：`package_type = "header-library"` + `package_id()` 清空，
    包内只有 include/experimental/** 与 licenses/LICENSE。
  * `build()` 对上游 CMake 工程做 configure + build 一致性校验（INTERFACE
    目标不编译任何翻译单元），并把 MDSPAN_ENABLE_TESTS / EXAMPLES /
    BENCHMARKS / COMP_BENCH 全部显式钉为 OFF——上游测试树默认会在 configure
    阶段用 `ExternalProject` 联网克隆 googletest（`GIT_TAG main` 移动靶），
    G2 干净轮必须纯离线。
  * 平台可移植性（W0-3 三步裁量）：交付头树 grep ISA 专属头/内联汇编/
    glibc printf 钩子族均 0 命中；系统 include 全集只有 C++ 标准库头
    （`<concepts>`/`<span>`/`<version>` 均在特性测试宏守卫内），
    无 `.S` 汇编、无 arch 目录 → 判可移植，无补丁（patches_applied: []）。
  * 上游测试（tests/ gtest 14 个可执行 + compilation_tests/ 14 个编译期
    测试可执行）在设备端用原生 CMake 单独构建运行，见
    test_package/MANIFEST.yml 的 `upstream_test_in_build: false` 与取数命令。
  * `cmake_file_name` / `cmake_target_name` 对齐上游 `install(EXPORT
    mdspanTargets NAMESPACE std::)` 的导出名：`find_package(mdspan)` +
    `std::mdspan`（examples/CMakeLists.txt 同口径）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class MdspanConan(ConanFile):
    name = "mdspan"
    version = "0.6.0"
    package_type = "header-library"

    description = ("Reference implementation of the C++ multidimensional array "
                   "accessor/view proposal P0009 (mdspan/mdarray), header-only")
    homepage = "https://github.com/kokkos/mdspan"
    license = "Apache-2.0 WITH LLVM-exception"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 MDSPAN_ENABLE_* 四项默认即 Off，这里逐项显式钉死：
        # 任何一项打开都会把 tests/（联网拉 googletest，GIT_TAG main）、
        # examples/（find_package(mdspan) 自引用）、benchmarks/（find_package(benchmark)
        # + Ruby metabench）拉进 configure，G2 干净轮必须离线自包含。
        for opt in ("MDSPAN_ENABLE_TESTS", "MDSPAN_ENABLE_EXAMPLES",
                    "MDSPAN_ENABLE_BENCHMARKS", "MDSPAN_ENABLE_COMP_BENCH"):
            tc.cache_variables[opt] = "OFF"
        tc.generate()

    def build(self):
        # header-only：INTERFACE 目标不编译任何翻译单元；configure + build
        # 的价值是校验补丁后的上游 CMake 工程仍自洽（真实日志，不伪造，R34）。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 交付树 = 上游 include/experimental/**（21 个文件，含无扩展名的
        # `experimental/mdspan` 与 `experimental/mdarray` 两个汇总头），
        # 整目录按相对路径拷贝，保证 `#include <experimental/mdspan>` 可用。
        copy(self, "*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # header-only：无编译产物，单一 package_id 服务所有配置（模板变体 A）。
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # 对齐上游 install(EXPORT mdspanTargets NAMESPACE std::) 与
        # examples/CMakeLists.txt 的 `find_package(mdspan)` + `std::mdspan`。
        self.cpp_info.set_property("cmake_file_name", "mdspan")
        self.cpp_info.set_property("cmake_target_name", "std::mdspan")
        # 上游头最低 C++14（MDSPAN_CXX_STANDARD DETECT 探测 14..23）；
        # 本机 OHOS profile 钉 cppstd=17，设备端上游测试在 C++17 与 C++20
        # 两个标准下各跑一轮（见 notes.md 验证结果），故不强加 -std 覆盖。
