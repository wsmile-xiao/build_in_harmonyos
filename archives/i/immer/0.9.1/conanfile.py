#!/usr/bin/env python3
"""Conan recipe — immer 0.9.1 (CMake header-only persistent data structures).

immer 是 C++ 持久化/不可变数据结构库（header-only，CMake INTERFACE target
`immer`，导出 ImmerConfig）。无第三方运行时依赖；可选依赖 Boehm-GC / RRB /
Boost 仅在构建上游完整测试/benchmark 时用到，本配方构建常规测试时关闭。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ImmerConan(ConanFile):
    name = "immer"
    version = "0.9.1"
    description = "Persistent and immutable data structures in C++ (header-only): vector, flex_vector, map, set, table, array with structural sharing"
    license = "BSL-1.0"
    homepage = "https://github.com/arximboldi/immer"
    url = ""  # CI fills this
    topics = ("persistent", "immutable", "functional", "header-only", "cpp14")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # 上游源码根目录含 Bazel BUILD 文件；在大小写不敏感文件系统上
        # cmake_layout 的 build/ 目录会与之冲突（NotADirectoryError），
        # 故使用不与上游文件重名、且大小写无关的构建目录名。
        self.folders.source = "."
        self.folders.build = "cmake-build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # header-only 包：上游单测由 test_package 消费者验证替代（同 ankerl
        # 先例）。上游测试依赖 Catch2（当前执行端 registry 策略禁用、缓存无），
        # 开启 imer_BUILD_TESTS 会在 find_package(Catch2) 处失败。
        tc.variables["immer_BUILD_TESTS"] = False
        tc.variables["immer_BUILD_EXAMPLES"] = False
        tc.variables["immer_BUILD_DOCS"] = False
        tc.variables["immer_BUILD_EXTRAS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 对齐上游 CMake 导出：find_package(Immer) + target `immer`
        self.cpp_info.set_property("cmake_file_name", "Immer")
        self.cpp_info.set_property("cmake_target_name", "immer")
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
