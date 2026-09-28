#!/usr/bin/env python3
"""Conan recipe for fancyargumentparser 1.0.4 — single-header C++ argument parser.

Header-only library: no build step, package copies argparse.h (+ argparse.ixx
C++20 module interface) to include/.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import apply_conandata_patches, get, export_conandata_patches
from conan.tools.layout import basic_layout


class FancyargumentparserConan(ConanFile):
    name = "fancyargumentparser"
    version = "1.0.4"
    description = "FancyArgumentParser — single-header C++ command-line argument parser (Python-like argparse API)"
    license = "MIT"
    homepage = "https://github.com/simfeo/FancyArgumentParser"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        check_min_cppstd(self, 11)

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        os.makedirs(include_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "argparse.h"),
                     os.path.join(include_dir, "argparse.h"))
        shutil.copy2(os.path.join(self.source_folder, "argparse.ixx"),
                     os.path.join(include_dir, "argparse.ixx"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fancyargumentparser")
        self.cpp_info.set_property("cmake_target_name", "fancyargumentparser::fancyargumentparser")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []