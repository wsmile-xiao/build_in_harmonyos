#!/usr/bin/env python3
"""Conan recipe — tree-sitter 0.25 (Makefile project).

tree-sitter uses a pure Makefile build system (no configure).
Key rules:
  - R9:  Use make -j1
  - R33: Compiler name hardcoded (clang), Conan profile sets PATH
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TreesitterConan(ConanFile):
    name = "tree-sitter"
    version = "0.25"
    description = "An incremental parsing system for programming tools"
    license = "MIT"
    homepage = "https://tree-sitter.github.io/tree-sitter/"
    url = "https://github.com/tree-sitter/tree-sitter"

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

    def build(self):
        apply_conandata_patches(self)
        self.run(f"make -C {self.source_folder} CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1")

    def package(self):
        copy(self, "*.h", os.path.join(self.source_folder, "lib", "include"),
             os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "*.so*", self.source_folder,
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "*.a", self.source_folder,
                 os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["tree-sitter"]
        self.cpp_info.includedirs = ["include"]
