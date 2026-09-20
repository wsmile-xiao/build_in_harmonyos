#!/usr/bin/env python3
"""Conan recipe — libcester 0.4 (header-only C unit testing framework).

Cester is a single-header C testing framework: the whole implementation
lives in include/exotic/cester.h and is included directly by consumers
(#include <exotic/cester.h>), so nothing is compiled or linked here.
The upstream test/ directory contains standalone test programs built
against the header, not part of the distributed product, hence no
commands.json and no bin/ output (R38: library package, not a CLI tool).

Consumer usage (auto-generated main, no CESTER_MAIN needed):

    #include <exotic/cester.h>
    CESTER_TEST(suite_name, inst, cester_assert_int_eq(1, 1); )
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibcesterConan(ConanFile):
    name = "libcester"
    version = "0.4"
    description = "A robust header only unit testing framework for C with function mocking, memory leak detection and crash report"
    license = "MIT"
    homepage = "https://github.com/exoticlibraries/libcester"
    url = ""  # CI fills this

    package_type = "header-library"

    # Header-only: no compiled artifacts, but keep settings for structure
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No compilation step: header-only library (no fake build logs).
        apply_conandata_patches(self)

    def package(self):
        copy(self, "cester.h", src=os.path.join(self.source_folder, "include", "exotic"),
             dst=os.path.join(self.package_folder, "include", "exotic"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # no build/compiler dependency -> single package_id

    def package_info(self):
        # Header-only: headers only, no libs, no bins.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "libcester")
        self.cpp_info.set_property("cmake_target_name", "libcester::libcester")
        self.cpp_info.includedirs = ["include"]