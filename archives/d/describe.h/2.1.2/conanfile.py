#!/usr/bin/env python3
"""Conan recipe — describe.h 2.1.2 (Makefile project, BDD test framework).

describe.h is a tiny BDD describe/it test framework (C99) by Stephen Mathieson.
The official 2.1.2 tarball does NOT vendor its two upstream deps that the
Makefile expects under deps/ (they are fetched here from their official
GitHub sources):
  - assertion-macros.h 0.3.1  (stephenmathieson/assertion-macros.h)
  - console-colors.c 1.0.1    (Constellation/console-colors.c)

Build: compile describe.c + console-colors.c into a static lib (libdescribe.a).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DescribeHConan(ConanFile):
    name = "describe.h"
    version = "2.1.2"
    description = "Simple BDD describe/it test framework for C (header + tiny impl)"
    license = "MIT"
    homepage = "https://github.com/stephenmathieson/describe.h"
    url = ""  # CI 注入制品仓地址，本仓既有约定保留为空（见其他已合入配方）

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # In-source build: the Makefile is CWD-relative
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Fetch the two upstream deps that the 2.1.2 tarball does not vendor.
        # NOTE: get(..., destination=...) does NOT strip the archive's root dir
        # (file lands in deps/<dep>/<repo>-<ver>/...), so unpack to the source
        # root (strip_root works) and then copy files into deps/<dep>/.
        for dep_dir, info in self.conan_data.get("deps", {}).items():
            get(self, url=info["url"], sha256=info["sha256"], strip_root=True)
        dep_files = {
            "assertion-macros": ["assertion-macros.h"],
            "console-colors": ["console-colors.h", "console-colors.c"],
        }
        for dep_dir, files in dep_files.items():
            for f in files:
                copy(self, f, self.source_folder,
                     os.path.join(self.source_folder, "deps", dep_dir))

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        self.run(f"{cc} -std=c99 -Wall -Wextra -Ideps -O2 -fPIC -c -o describe.o describe.c")
        self.run(f"{cc} -std=c99 -Wall -Wextra -Ideps -O2 -fPIC -c -o console-colors.o deps/console-colors/console-colors.c")
        self.run(f"{ar} rcs libdescribe.a describe.o console-colors.o")

    def package(self):
        # Header + upstream dep headers (kept in their include subdirs)
        copy(self, "describe.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "assertion-macros.h",
             os.path.join(self.source_folder, "deps", "assertion-macros"),
             os.path.join(self.package_folder, "include", "assertion-macros"))
        copy(self, "console-colors.h",
             os.path.join(self.source_folder, "deps", "console-colors"),
             os.path.join(self.package_folder, "include", "console-colors"))
        # Static library
        copy(self, "libdescribe.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = ["describe"]
        self.cpp_info.set_property("cmake_file_name", "describe.h")
        self.cpp_info.set_property("cmake_target_name", "describe.h::describe.h")