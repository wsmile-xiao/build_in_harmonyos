#!/usr/bin/env python3
"""Conan recipe — functionalplus 0.2.26 (header-only CMake library).

FunctionalPlus（上游 fplus/FunctionalPlus）是 header-only C++14 函数式工具库：
- package_type="header-library" + implements auto_header_only_mode（单一 package_id）；
- package() 只交付 include/ 树与 licenses/LICENSE，无编译产物（源码零改动、零补丁）；
- 上游测试面（rule4/R51）：test/ 下 39 个 doctest 测试程序，被审 v0.2.26 源码宏
  423 例、框架注册（ctest -N）423 例、运行期断言 1662 条；上游当前 HEAD 源码宏 424
  （差 1 = result_test.cpp 的 compose_first_error_and_result 用例，依赖被审版本
  不存在的 API，逐项归因，见 test_package/MANIFEST.yml 与 notes.md）。
  本配方 build() 不编译上游测试（header-only 无编译面；与同上游已发布包
  archives/f/fplus/0.2.28 的 upstream_test_in_build=false 先例一致），上游测试在
  设备侧沙箱 HOME 独立构建运行，记录于 reports/test-report.md。
"""
from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class FunctionalplusConan(ConanFile):
    name = "functionalplus"
    version = "0.2.26"
    description = "FunctionalPlus - helps you write concise and readable C++ code (header-only fplus library)"
    license = "BSL-1.0"
    homepage = "https://github.com/Dobiasd/FunctionalPlus"
    url = "https://github.com/Dobiasd/FunctionalPlus"

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "compiler", "build_type", "arch"

    # header-only：源码只读，build()/package() 直接从 source_folder 读取
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Header-only：无编译产物，仅应用补丁（本版本 patches 为空）。
        # 上游 doctest 测试套件不在 build() 内编译，理由与运行证据见 notes.md。
        apply_conandata_patches(self)

    def package(self):
        # header-only：把上游 include 树与许可证原样交付
        copy(self, pattern="*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, pattern="LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        # 与上游 CMake 导出目标一致：find_package(FunctionalPlus) + FunctionalPlus::fplus
        self.cpp_info.set_property("cmake_file_name", "FunctionalPlus")
        self.cpp_info.set_property("cmake_target_name", "FunctionalPlus::fplus")
        self.cpp_info.components["fplus"].libs = []
        self.cpp_info.components["fplus"].set_property("cmake_target_name", "FunctionalPlus::fplus")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
