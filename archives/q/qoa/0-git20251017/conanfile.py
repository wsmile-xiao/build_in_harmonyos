#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class QoaConan(ConanFile):
    name = "qoa"
    version = "0-git20251017"
    description = ("Quite OK Audio Format — single-header lossy audio "
                   "codec (fast, ~4:1, MIT)")
    license = "MIT"
    homepage = "https://github.com/phoboslab/QOA"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

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

    def package(self):
        copy(self, "qoa.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "qoa")
        self.cpp_info.set_property("cmake_target_name", "qoa::qoa")
