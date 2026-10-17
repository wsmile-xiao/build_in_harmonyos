#!/usr/bin/env python3
"""Conan recipe for stb_sprintf 1.10.0."""

import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class StbSprintfConan(ConanFile):
    name = "stb_sprintf"
    version = "1.10.0"
    description = "Single-header sprintf and snprintf implementation for C and C++"
    license = "Public-Domain"
    homepage = "https://github.com/nothings/stb"
    url = "https://github.com/nothings/stb"
    topics = ("sprintf", "snprintf", "formatting", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Header-only package: the consumer test_package performs the runtime
        # API check. The upstream test_sprintf.c is declared and executed
        # separately during adaptation; current master fails its %b assertion.

    def package(self):
        copy(self, "stb_sprintf.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "stb_sprintf")
        self.cpp_info.set_property("cmake_target_name", "stb_sprintf::stb_sprintf")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
