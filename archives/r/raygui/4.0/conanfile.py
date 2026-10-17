#!/usr/bin/env python3
"""Conan recipe - raygui 4.0 (header-only immediate-mode GUI library)."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RayguiConan(ConanFile):
    name = "raygui"
    version = "4.0"
    description = "A simple and easy-to-use immediate-mode GUI library (header-only)"
    license = "zlib"
    homepage = "https://github.com/raysan5/raygui"
    url = ""
    topics = ("gui", "immediate-mode", "header-only", "ui")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def build(self):
        # header-only 无编译阶段；验证器要求显式补丁调用（当前 patches 为空，no-op）
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(self, "raygui.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
