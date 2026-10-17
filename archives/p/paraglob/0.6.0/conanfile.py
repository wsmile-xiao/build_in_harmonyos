#!/usr/bin/env python3
"""Conan recipe — paraglob 0.6.0 (CMake / C++17).

Paraglob: a fairly quick data structure for matching a string against a
large list of patterns (Zeek 子组件，上游 github.com/zeek/paraglob).

构建入口判定：manifest `build.system: cmake`（实测为准——上游根目录的
`configure` 只是 CMake 便捷包装，init-build 因 BUILD_SYSTEM env 优先级
最高把它误判成 autotools，已手工改回 cmake，见 notes.md 问题表 #1）。

依赖：**零外部库**。Aho-Corasick 以 vendored 源码（src/ahocorasick/）直接
并入 libparaglob.a，`find_package|pkg_check_modules|ExternalProject|
FetchContent|pkg-config` 全部零命中 → requirements() 为空集，
`conan install --build=missing` 实测 rc=0 空依赖图（W0-2 证据）。

shared 语义（xplc/meschach 先例：库型必声明 shared、纯 package_id 语义不注旗）：
上游 `src/CMakeLists.txt` 硬编码 `add_library(paraglob STATIC ...)`，
`BUILD_SHARED_LIBS` 对产物无影响 → 保留 options/default_options 作
package_id 语义，**generate() 不注入任何构建旗标**，恒静态。

产物（原生 `cmake --install` 实测清点 6 件）：
  bin/paraglob-test       —— 上游 CLI/benchmark 驱动（btest 套件的被测程序）
  lib/libparaglob.a       —— 静态库（内含 vendored ahocorasick 目标文件）
  include/paraglob/*.h    —— 4 个公开头
另按惯例把上游 COPYING 拷到 licenses/。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, \
    export_conandata_patches, get


class ParaglobConan(ConanFile):
    name = "paraglob"
    version = "0.6.0"
    description = ("A fairly quick data structure for matching a string "
                   "against a large list of patterns (Zeek)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/zeek/paraglob"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # 库型必声明 shared（conan graph info 硬校）；上游硬编码 STATIC，
    # 故本选项只参与 package_id，不注入 BUILD_SHARED_LIBS 旗标。
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-2 硬依赖空集：vendored ahocorasick，零外部库；无 tool_requires。
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # CI 预下载器可能把 url 改写成 [mirror, official] 候选列表，
        # conan 的 get() 原生支持两种形态。
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 不注入 BUILD_SHARED_LIBS（上游 STATIC 硬编码，注入即假旗标）；
        # CMAKE_BUILD_TYPE 由 settings.build_type 经 CMakeToolchain 传递
        # （ci profile build_type=Release，上游 CMakeLists 兜底亦为 Release）。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 与原生 `cmake --install` 实测树一一对应（6 件）：
        # lib/libparaglob.a + include/paraglob/*.h(4) + bin/paraglob-test
        self.cpp_info.libs = ["paraglob"]
        self.cpp_info.bindirs = ["bin"]   # 装有 CLI → 软件级 commands.json（PF8/L0k）
        # includedirs/libdirs 用默认 include/，与 install 树一致
