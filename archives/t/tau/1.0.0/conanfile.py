#!/usr/bin/env python3
"""Conan recipe — tau 1.0.0 (Muon: header-only C/C++ micro unit testing framework).

Header-only 变体 A：无编译，仅打包头文件。
Muon 公开头文件位于 Muon/ 目录（Muon.h, Misc.h, Types.h, Compilers.h），
消费者以 `#include <Muon/Muon.h>` 使用。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TauConan(ConanFile):
    name = "tau"
    version = "1.0.0"
    description = "Muon (tau) — A Micro Unit Testing Framework for C/C++ (header-only)"
    license = "MIT"
    homepage = "https://github.com/jasmcaus/tau"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译阶段；补丁（若有）在源码目录应用
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "Muon"),
             dst=os.path.join(self.package_folder, "include", "Muon"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "tau")
        self.cpp_info.set_property("cmake_target_name", "tau::tau")
        self.cpp_info.includedirs = ["include"]
