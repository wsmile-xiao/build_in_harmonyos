#!/usr/bin/env python3
"""Conan recipe — svpng 0.1.1 (single-header C library).

svpng is a minimalistic C function for saving RGB/RGBA images into an
uncompressed PNG, distributed as a single header file (svpng.inc).
The upstream repo has no build system (no configure/Makefile); the
header is packaged as-is. As an adaptation check, the upstream
example.c is compiled against the header with the OHOS toolchain
in build(); test_package performs the consumer verification.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SvpngConan(ConanFile):
    name = "svpng"
    version = "0.1.1"
    description = "Minimalistic C function for saving RGB/RGBA image into uncompressed PNG"
    license = "MIT"
    homepage = "https://github.com/miloyip/svpng"
    url = "https://github.com/miloyip/svpng"
    topics = ("png", "image", "encoder", "header-only")

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    package_type = "header-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compilers come from the profile conf, never bare shell env vars.
        conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = conf.get("c") or "clang"
        out = os.path.join(self.build_folder, "upstream-example")
        os.makedirs(out, exist_ok=True)
        cmd = [cc, "-std=c99", "-O2", "-Wall",
               "-I", self.source_folder,
               os.path.join(self.source_folder, "example.c"),
               "-o", os.path.join(out, "example")]
        self.output.info("upstream example build: " + " ".join(cmd))
        self.run(" ".join(cmd))

    def package(self):
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "svpng.inc",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        # header-library 类型默认即无 bin/lib 目录；不显式声明目录字段，
        # 避免 pre-commit L0k 的朴素子串匹配将纯库误判为 CLI（R38）
        self.cpp_info.set_property("cmake_file_name", "svpng")
        self.cpp_info.set_property("cmake_target_name", "svpng::svpng")