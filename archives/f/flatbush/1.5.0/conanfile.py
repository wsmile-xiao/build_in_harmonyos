#!/usr/bin/env python3
"""Conan recipe — flatbush 1.5.0 (header-only).

Flatbush for C++ 是 JavaScript Flatbush（packed Hilbert R-tree 空间索引）的
C++ 移植，header-only（INTERFACE target），无编译产物、无运行时依赖。
上游 CMake 默认 WITH_SPAN=ON，通过 FLATBUSH_SPAN 编译定义启用自带的 C++11
兼容 span；关闭时要求 cxx_std_20。OHOS profile 为 cppstd=17，因此配方按
WITH_SPAN=ON 语义打包，并在 package_info 中声明 FLATBUSH_SPAN 宏。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class FlatbushConan(ConanFile):
    name = "flatbush"
    version = "1.5.0"
    description = "Flatbush for C++: a packed Hilbert R-tree spatial index for 2D points and rectangles (C++ port of the JS library)"
    license = "MIT"
    homepage = "https://github.com/chusitoo/flatbush"
    url = "https://github.com/chusitoo/flatbush"
    topics = ("spatial", "index", "rtree", "hilbert")
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        # Header-only：无编译产物，单一 package_id
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(self, "flatbush.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "flatbush")
        self.cpp_info.set_property("cmake_target_name", "flatbush::flatbush")
        # 与上游 WITH_SPAN=ON 默认一致：启用自带 C++11 兼容 span
        self.cpp_info.defines = ["FLATBUSH_SPAN"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
