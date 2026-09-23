#!/usr/bin/env python3
"""Conan recipe — qsort 0.1 (header-only C macro library).

qsort 是一个以 C 宏实现的经典快速排序库（Robert Sedgewick 1978 论文），
单头文件 qsort.h，无编译产物；bench.cc 仅用于基准测试，不入包。
header-only，无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class QsortConan(ConanFile):
    name = "qsort"
    version = "0.1"
    description = "Quicksort as a C macro (Sedgewick 1978), single-header header-only library"
    license = "MIT"
    homepage = "https://github.com/svpv/qsort"
    url = ""  # CI fills this
    topics = ("qsort", "quicksort", "header-only", "c-macro", "sorting")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        copy(self, "qsort.h", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # header-only 库：无编译产物，E257 no-op-build-for-header-only
        pass

    def package(self):
        copy(self, "qsort.h", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qsort")
        self.cpp_info.set_property("cmake_target_name", "qsort::qsort")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
