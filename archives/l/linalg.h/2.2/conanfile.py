#!/usr/bin/env python3
"""Conan recipe — linalg.h 2.2 (header-only, single-header public domain).

linalg.h is a single-header, public domain (Unlicense), short vector math
library for C++11. It is dependency-free and defines no symbols in the
public namespace. Packaging only copies the header; no build step.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LinalgHConan(ConanFile):
    name = "linalg.h"
    version = "2.2"
    description = "Single-header public domain short vector math library for C++"
    license = "Unlicense"
    homepage = "https://github.com/sgorsten/linalg"
    url = ""  # CI fills this
    topics = ("math", "vector", "matrix", "quaternion", "header-only", "single-header")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: no compile step. Upstream tests are covered by
        # test_package (consumer view) — see MANIFEST.yml for the ledger.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "linalg.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "UNLICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "linalg.h")
        self.cpp_info.set_property("cmake_target_name", "linalg.h::linalg.h")

    def package_id(self):
        self.info.clear()
