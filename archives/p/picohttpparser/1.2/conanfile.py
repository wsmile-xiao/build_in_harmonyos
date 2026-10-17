#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Picohttpparser, picohttpparser, 1.2, picohttpparser 1.2, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PicohttpparserConan(ConanFile):
    name = "picohttpparser"
    version = "1.2"
    description = "picohttpparser 1.2"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder + "/picohttpparser.c"
        obj = self.build_folder + "/picohttpparser.o"
        archive = self.build_folder + "/libpicohttpparser.a"
        self.run(f"clang -fPIC -O2 -c {source} -o {obj}", env="conanbuild")
        self.run(f"llvm-ar rcs {archive} {obj}", env="conanbuild")

    def package(self):
        copy(self, "picohttpparser.h", dst=self.package_folder + "/include", src=self.source_folder)
        copy(self, "libpicohttpparser.a", dst=self.package_folder + "/lib", src=self.build_folder)

    def package_info(self):
        self.cpp_info.libs = ["picohttpparser"]
