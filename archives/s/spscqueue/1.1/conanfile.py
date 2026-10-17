#!/usr/bin/env python3
"""Conan recipe — spscqueue 1.1 (header-only C++11 library).

rigtorp/SPSCQueue: single-producer single-consumer wait-free & lock-free
fixed-size queue, header-only (CMake INTERFACE library, cxx_std_11).
No compilation needed; package installs the single public header.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class SpscqueueConan(ConanFile):
    name = "spscqueue"
    version = "1.1"
    description = "Single-producer single-consumer wait-free and lock-free fixed size queue written in C++11"
    license = "MIT"
    homepage = "https://github.com/rigtorp/SPSCQueue"
    url = "https://github.com/rigtorp/SPSCQueue"
    topics = ("spsc", "queue", "lock-free", "wait-free", "header-only", "cpp11")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: no compilation. Apply any conandata patches (none for v1.1).
        apply_conandata_patches(self)

    def package(self):
        # Header-only: only the public header is installed.
        copy(
            self,
            "SPSCQueue.h",
            src=os.path.join(self.source_folder, "include", "rigtorp"),
            dst=os.path.join(self.package_folder, "include", "rigtorp"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "spscqueue")
        self.cpp_info.set_property("cmake_target_name", "spscqueue::spscqueue")