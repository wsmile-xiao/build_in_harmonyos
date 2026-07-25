#!/usr/bin/env python3
"""Conan recipe — clang-build-analyzer 1.6.0 (CMake C++17 CLI tool).

ClangBuildAnalyzer 分析 clang -ftime-trace 生成的编译时间追踪数据,
输出编译耗时报告。无外部 conan 依赖,所有第三方库
(cwalk/inih/xxHash/enkiTS/llvm-Demangle/simdjson)均 vendored 在 src/external/。
产物为可执行文件 ClangBuildAnalyzer,安装到 bin/。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ClangBuildAnalyzerConan(ConanFile):
    name = "clang-build-analyzer"
    version = "1.6.0"
    description = "Tool to analyze compilation time from clang -ftime-trace output"
    license = "Unlicense"
    homepage = "https://github.com/aras-p/ClangBuildAnalyzer"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        # 将 OHOS 映射为 Linux,让 CMake 正确识别目标平台
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            # 从 settings.arch 动态映射 CMAKE_SYSTEM_PROCESSOR
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch_map.get(
                str(self.settings.arch), str(self.settings.arch)
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 拷贝 license 文件
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # TOOL 类型:只导出 bindirs,无 libs/includedirs/libdirs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
