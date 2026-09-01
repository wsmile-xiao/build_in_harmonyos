#!/usr/bin/env python3
"""Conan recipe - debug_assert 1.3.0 (single-header header-only library)."""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class DebugAssertConan(ConanFile):
    name = "debug_assert"
    version = "1.3.0"
    description = "Simple, flexible and modular assertion macro for C++"
    license = "Zlib"
    homepage = "https://github.com/foonathan/debug_assert"
    url = "https://github.com/foonathan/debug_assert"
    topics = ("assert", "assertion", "debug", "header-only", "c++")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译期产物；仍应用补丁（当前 patches: {} 为空，保持标准配方骨架）
        apply_conandata_patches(self)

    def package(self):
        # 头文件打包两次：include/（支持无前缀 #include "debug_assert.hpp"）
        # 与 include/debug_assert/（支持 #include <debug_assert/debug_assert.hpp>）
        copy(self, "debug_assert.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "debug_assert.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include", "debug_assert"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "debug_assert")
        self.cpp_info.set_property("cmake_target_name", "debug_assert::debug_assert")
