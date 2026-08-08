#!/usr/bin/env python3
"""Conan recipe for abc 0.0.0.20260511 — Berkeley ABC logic synthesis tool (Makefile)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AbcConan(ConanFile):
    name = "abc"
    version = "0.0.0.20260511"
    description = "ABC: System for Sequential Logic Synthesis and Formal Verification"
    license = "MIT"
    homepage = "https://github.com/berkeley-abc/abc"
    url = "https://github.com/berkeley-abc/abc"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # abc 是 in-source 构建（Makefile 在源码根目录，无 configure）
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf (dict form, conan 2.29.1 兼容), never bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        # abc 是纯 Makefile 项目（无 configure）。readline 为可选依赖
        # （制品仓无 readline 预编译包），用 ABC_USE_NO_READLINE 禁用。
        # Makefile 编译 C++ 文件（src/map/if/acd/*.cpp 等）默认用 g++，
        # 必须显式传 CXX，否则 OHOS 环境报 "g++: No such file or directory"。
        # R9: 用 -j1 保证可复现构建。
        self.run(
            f"make CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} "
            f"ABC_USE_NO_READLINE=1 -j1"
        )

    def package(self):
        # abc 无 make install 目标，二进制生成在源码根目录，手动安装到 bin/
        copy(self, "abc", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
