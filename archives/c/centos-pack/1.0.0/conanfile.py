#!/usr/bin/env python3
"""Conan recipe for CentPack — Pure Makefile project.

CentPack is a generic numerical solver for hyperbolic conservation laws.
Uses pure Makefile (no configure script).
"""
from conan import ConanFile
from conan.tools.files import get, copy, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class CentospackConan(ConanFile):
    name = "centos-pack"
    version = "1.0.0"
    description = "A generic numerical solver for hyperbolic conservation laws"
    license = "Custom (Research and instructional use)"
    homepage = "https://github.com/etadmor/centpack"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["1.0.0"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 补丁已经修改了 Makefile (g++ → clang++)，直接编译
        # 创建 lib 目录
        os.makedirs(os.path.join(self.source_folder, "lib"), exist_ok=True)
        
        # 编译库
        self.run("make libs", cwd=self.source_folder)

    def package(self):
        # 打包头文件
        copy(self, "*.h", 
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        
        # 打包库文件
        copy(self, "*.a",
             src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)

    def package_info(self):
        # CentPack 提供 6 个静态库
        self.cpp_info.libs = [
            "centpack_1d_FD2",
            "centpack_1d_SD2", 
            "centpack_1d_SD3",
            "centpack_2d_FD2",
            "centpack_2d_SD2",
            "centpack_2d_SD3",
            "array"
        ]
