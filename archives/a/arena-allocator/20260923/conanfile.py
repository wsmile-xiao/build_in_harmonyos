#!/usr/bin/env python3
"""Conan recipe — arena-allocator 20260923 (header-only C89 arena allocator).

arena-allocator (https://github.com/ccgargantua/arena-allocator) is a
single-header C library (arena.h). The implementation is emitted by defining
ARENA_IMPLEMENTATION in one translation unit, or by compiling the bundled
arena.c convenience TU. Upstream has no configure/install target (the Makefile
only builds tests/examples), so this recipe packages the public header and the
convenience arena.c source into include/ — header-only packaging.

R32 align: no settings.os branch needed; os=OHOS is mapped by the OHOS-adapted
conan toolchain.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class ArenaAllocatorConan(ConanFile):
    name = "arena-allocator"
    version = "20260923"
    description = "Super small, simple, (almost) completely C89-compliant single-header arena allocator"
    license = "Apache-2.0"
    homepage = "https://github.com/ccgargantua/arena-allocator"
    url = "https://github.com/ccgargantua/arena-allocator"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # 无编译阶段：header-only 库，无 configure/make；build() 仅应用配方补丁
    # （当前 patches 为空集，无伪造编译日志——R34）
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "arena.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "arena.c", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建产物 → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "arena-allocator")
        self.cpp_info.set_property("cmake_target_name", "arena-allocator::arena-allocator")