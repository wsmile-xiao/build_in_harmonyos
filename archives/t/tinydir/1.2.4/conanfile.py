#!/usr/bin/env python3
"""Conan recipe — tinydir 1.2.4 (header-only C library).

tinydir is a lightweight, portable C directory/file reader wrapping
dirent (POSIX) / FindFirstFile (Windows). Header-only: no build().
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TinydirConan(ConanFile):
    name = "tinydir"
    version = "1.2.4"
    description = "Lightweight, portable and easy to integrate C directory and file reader"
    license = "BSD-2-Clause"
    homepage = "https://github.com/cxong/tinydir"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译阶段，仅应用补丁（当前 patches 为空）
        apply_conandata_patches(self)

    def package(self):
        import os as _os
        # header-only：拷贝头文件到包内 include/（dst 用绝对路径，避免相对解析歧义）
        copy(self, "*.h", src=self.source_folder,
             dst=_os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp", src=self.source_folder,
             dst=_os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=_os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.set_property("cmake_file_name", "tinydir")
        self.cpp_info.set_property("cmake_target_name", "tinydir::tinydir")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
