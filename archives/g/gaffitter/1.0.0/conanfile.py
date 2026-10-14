#!/usr/bin/env python3
"""Conan recipe — gaffitter 1.0.0 (Genetic Algorithm File Fitter).

- 上游: SourceForge (Douglas A. Augusto), GPL-3.0-or-later, C++ (~5100 行)
- 构建系统: CMake（cmake_minimum_required(VERSION 2.4)，纯 add_library/
  add_executable/install，无第三方依赖）
- 产物: bin/fit — 命令行工具，把文件/条目组合进固定容量卷（装箱问题），
  通过遗传算法最小化所需卷数
- 依赖: 无（纯 C++ 标准库 + POSIX stat/lstat/readdir）

OHOS 要点:
  * 上游 2015 年的 CMakeLists.txt 声明 cmake_minimum_required(VERSION 2.4)；
    CMake >= 4.0 移除了 < 3.5 兼容模式会直接报错。按 CMake 官方文档传入
    CMAKE_POLICY_VERSION_MINIMUM=3.5（专为此类"无法修改 CMakeLists 的旧
    项目"提供的机制），等效于把策略最低版本提升到 3.5 —— 无需 patch。
  * 代码为纯 POSIX（sys/stat.h、dirent.h、unistd.h、rand/srand），musl
    libc 完整覆盖，无 __OHOS__/OS 分支、无 patch。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class GaffitterConan(ConanFile):
    name = "gaffitter"
    version = "1.0.0"
    description = "Genetic Algorithm File Fitter: fits files/items into fixed-size volumes (e.g. CD/DVD) minimizing the number of volumes via a genetic algorithm"
    license = "GPL-3.0-or-later"
    homepage = "https://gaffitter.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # gaffitter 1.0.0（2015）使用 std::random_shuffle：C++14 起弃用、
        # C++17 起从标准移除，libc++ 在 C++17 模式下不再提供该符号。
        # 本包以 C++14 编译（无源码 patch；应用为终端产物，无下游 ABI
        # 消费方，钉死标准不影响兼容性）。
        self.settings.compiler.cppstd = "14"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(VERSION 2.4) vs CMake >= 4.0：
        # 官方兼容机制（E103 回退方案 / E187 推荐方案，
        # cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5）。
        # 注意必须用 cache_variables（-D 命令行注入）：实测 tc.variables
        # 写入工具链文件的 set(... CACHE) 在 CMakeLists.txt:1 的
        # cmake_minimum_required() 求值时尚未加载，不生效。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # R26: 终端工具静态链接（上游 add_library 未指定类型，默认静态，
        # 显式声明防止 BUILD_SHARED_LIBS 环境泄漏）。
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
