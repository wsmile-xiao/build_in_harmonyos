#!/usr/bin/env python3
"""Conan recipe for libatomicbitvector — header-only atomic bitset/bitvector.

The task version 0.0-git20200519.e295358 pins the upstream snapshot at commit
e295358 (2019-2020, Erik Garrison / Facebook folly ConcurrentBitSet derived).
The package installs include/atomic_bitvector.hpp and include/iterator_tpl.h;
no runtime library is produced. Upstream ships only a manual concurrency demo
(src/main.cpp), so the test_package provides the functional checks.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibAtomicBitvectorConan(ConanFile):
    name = "libatomicbitvector"
    version = "0.0-git20200519.e295358"
    description = "Atomic bitset/bitvector with size fixed at runtime (header-only)"
    license = "Apache-2.0"
    homepage = "https://github.com/ekg/atomicbitvector"
    url = "https://github.com/ekg/atomicbitvector"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "atomic_bitvector.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "iterator_tpl.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "atomicbitvector")
        self.cpp_info.set_property("cmake_target_name", "atomicbitvector::atomicbitvector")
