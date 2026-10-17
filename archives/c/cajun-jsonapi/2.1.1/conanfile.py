#!/usr/bin/env python3
"""Conan recipe — cajun-jsonapi 2.1.1 (header-only JSON library).

cajun-jsonapi 是 fork 自 cajun 的 header-only C++ JSON 解析/序列化库
(仅头文件 + .inl 模板实现，无编译产物、无依赖)。配方按 header-library
打包 include/cajun/json/ 头文件，无系统同名库冲突问题 (R26 不适用)。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
import os


class CajunJsonapiConan(ConanFile):
    name = "cajun-jsonapi"
    version = "2.1.1"
    description = "CAJUN (C++ API for JSON) — a header-only JSON reader/writer library for C++"
    license = "BSD-2-Clause"
    homepage = "https://github.com/cajun-jsonapi/cajun-jsonapi"
    url = ""  # CI fills this
    topics = ("json", "parser", "header-only", "cpp11")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译产物；仅应用配方声明的补丁（当前无补丁）
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.inl", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cajun-jsonapi")
        self.cpp_info.set_property("cmake_target_name", "cajun-jsonapi::cajun-jsonapi")
        self.cpp_info.libs = []
        self.cpp_info.requires = []
