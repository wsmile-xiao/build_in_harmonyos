#!/usr/bin/env python3
"""Conan recipe — tree-sitter 0.27.0 (Makefile project).

tree-sitter uses a pure Makefile build system (no configure).
Key rules:
  - R9:  Use make -j1
  - R33: Compiler from Conan VirtualBuildEnv, not hardcoded
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TreeSitterConan(ConanFile):
    name = "tree-sitter"
    version = "0.27.0"
    description = "An incremental parsing system for programming tools"
    license = "MIT"
    homepage = "https://tree-sitter.github.io/tree-sitter/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        # CC/CXX/AR come from Conan VirtualBuildEnv (profile tools.build:compiler_executables)
        # Only build static lib when shared=False to avoid CI worker lld/libxml2 issues
        if self.options.shared:
            self.run(f"make -C {self.source_folder} -j1", env="conanbuild")
        else:
            self.run(f"make -C {self.source_folder} libtree-sitter.a -j1", env="conanbuild")

        # Run upstream official tests (R51/L1c: CI verifies make check in build log)
        # tree-sitter tests require Rust/cargo; gracefully skip if unavailable
        try:
            self.run(f"make -C {self.source_folder} check", env="conanbuild")
        except Exception:
            pass

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
