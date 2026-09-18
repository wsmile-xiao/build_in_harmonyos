#!/usr/bin/env python3
"""Conan recipe for libstb 0.0-git20250907.fede005 — OHOS aarch64 adaptation.

Upstream: nothings/stb @ fede005abaf93d9d7f3a679d1999b2db341b360f (2025-09-07).
libstb 打包 stb 单头文件库全集（20 个 stb_*.h + stb_vorbis.c），与仓库中已有的
单头包 stb_image/2.30、stb_ds/0.67、stb_sprintf、stb_image_write、stb_image_resize
同属一个上游仓库（且 stb_image/2.30 用的就是同一 commit fede005），但那些包只装
单个头文件；libstb 是合集包，一次安装全部 stb 头文件。

Header-only：无构建系统、无依赖。package() 复制根目录全部 stb_*.h 与 stb_vorbis.c
（stb_vorbis.c 是 vorbis 的官方 include-式实现文件，惯例上与头文件一起安装、由
消费者 #include 一次）到 include/，LICENSE 到 licenses/。
deprecated/ 目录的头文件不打包（上游已标记弃用，其中 deprecated/stb_image_resize.h
由根目录 stb_image_resize2.h 取代）。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# 根目录安装清单（fede005 快照）。conan copy() 的通配符会递归子目录，会把
# stb_image_resize_test/old_image_resize.h 等测试辅助文件误打进包，
# 故用显式清单逐个复制，只装根目录文件。
STB_FILES = [
    "stb_c_lexer.h", "stb_connected_components.h", "stb_divide.h", "stb_ds.h",
    "stb_dxt.h", "stb_easy_font.h", "stb_herringbone_wang_tile.h", "stb_hexwave.h",
    "stb_image.h", "stb_image_resize2.h", "stb_image_write.h", "stb_include.h",
    "stb_leakcheck.h", "stb_perlin.h", "stb_rect_pack.h", "stb_sprintf.h",
    "stb_textedit.h", "stb_tilemap_editor.h", "stb_truetype.h", "stb_voxel_render.h",
    "stb_vorbis.c",
]


class LibstbConan(ConanFile):
    name = "libstb"
    version = "0.0-git20250907.fede005"
    description = "stb single-file public domain / MIT licensed libraries for C/C++ (full collection: image, image_write, image_resize2, ds, sprintf, rect_pack, truetype, vorbis, dxt, divide, perlin, textedit, etc.)"
    license = ("MIT", "Unlicense")
    url = "https://github.com/nothings/stb"
    homepage = "https://github.com/nothings/stb"
    topics = ("header-only", "image", "audio", "font", "data-structures", "stb")

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    package_type = "header-library"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def package(self):
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for f in STB_FILES:
            copy(self, f,
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "libstb")
        self.cpp_info.set_property("cmake_target_name", "libstb::libstb")
        self.cpp_info.set_property("pkg_config_name", "libstb")
