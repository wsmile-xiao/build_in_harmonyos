#!/usr/bin/env python3
"""Conan recipe for uncrustify 0.79.0 — C/C++/C#/D/Java/Pawn/Vala 源码格式化工具.

uncrustify 是纯命令行应用（application）：CMake 构建产出单个 `uncrustify`
可执行文件，不产库、不装头文件。上游自带 CTest 套件（tests/*.test 驱动的
格式化回归 + 自身源码风格回归 + CLI 选项回归 + --help 冒烟），本配方在
build() 里用 cmake.test() 真实执行它。

OHOS 适配要点（详见 notes.md）：
* 0 个 Conan 依赖，构建只用 clang + cmake + python3（CTest 驱动脚本）；
* 上游 CMakeLists 要求 cmake_minimum_required(3.5)，CMake 4.x 直接可用，
  设备实测无需补丁（patches 为空）；
* 格式化输出与平台无关（纯文本比对），aarch64/OHOS 无行为差异。
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class UncrustifyConan(ConanFile):
    name = "uncrustify"
    version = "0.79.0"
    description = ("uncrustify: 源码格式化工具，支持 C/C++/C#/D/Java/"
                   "Objective-C/Pawn/Vala，命令行驱动，零第三方依赖")
    license = "GPL-2.0-or-later"
    homepage = "https://uncrustify.sourceforge.net/"
    url = "https://github.com/uncrustify/uncrustify"

    package_type = "application"

    # L0p/PF8: OHOS profile 需要全部四项 settings
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # Conan 2 只默认导出 conanfile.py + conandata.yml，
        # patches/ 必须显式导出否则 apply_conandata_patches 找不到文件。
        export_conandata_patches(self)

    def requirements(self):
        # 任务卡声明 0 依赖；上游 CMakeLists 亦无 find_package 外部库。
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 打开上游 CTest 套件（BUILD_TESTING 默认 ON，这里显式声明意图）：
        # tests/CMakeLists.txt 注册 11 个格式化套件 + sources_format +
        # cli_options + sanity，共 14 个 ctest 用例。
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 真实执行上游测试套件（R34：不是空壳，失败即 conan create 失败）。
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 许可证随包落 licenses/（归档规范：包内必须留许可文本）。
        copy(self, "COPYING", src=self.source_folder,
             dst=f"{self.package_folder}/licenses", keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
