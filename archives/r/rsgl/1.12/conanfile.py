#!/usr/bin/env python3
"""Conan recipe — rsgl 1.12 (Header-only C graphics library).

RSGL is a modular cross-platform graphics library that can be used as a
single-header library (define RSGL_IMPLEMENTATION in exactly one TU).
It bundles RGFW (windowing), RFont (text) and stb_image.h under deps/.
No X11 / GLX is required when RSGL_NO_RGFW (standalone graphics mode) is
used, which is the OHOS adaptation path (EGL/GLES3 loader provided by the
host application).

铁律对齐: R34（test_package 必须真实调用被测物——test.c 实际 include
并使用 RSGL API，不能只 print）；R51（上游测试三步法：RSGL 上游以
examples/ 下的 15 个示例程序为可运行入口，已在 test_package/MANIFEST.yml
与 notes.md 中清点申报）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class RsglConan(ConanFile):
    name = "rsgl"
    version = "1.12"
    description = "Riley's Simple Graphics Library - header-only C graphics library (OHOS/EGL-GLES3 mode)"
    license = "MIT"
    homepage = "https://github.com/ColleagueRiley/RSGL"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: no compilation. Cargo patches are applied here
        # (currently none) so the CI L0*/PF gate expectations hold. Real
        # compile-and-run verification happens in test_package (R34).
        apply_conandata_patches(self)

    def package(self):
        # Main headers at include/ (keep_path=True preserves deps/ prefix so
        # RSGL.h's `#include "deps/RFont.h"` resolves).
        copy(self, "RSGL.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "RSGL_gl.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "deps/*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only: single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.defines = ["RSGL_NO_RGFW", "RSGL_OPENGL_ES3"]