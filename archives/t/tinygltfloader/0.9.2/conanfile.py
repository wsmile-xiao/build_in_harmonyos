#!/usr/bin/env python3
"""Conan recipe for tinygltfloader 0.9.2.

TinyGLTFLoader is header-only. The upstream sample Makefile is still built
and run during package creation so that the shipped implementation headers are
compiled with the same warning policy as the source project.
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


class TinygltfloaderConan(ConanFile):
    name = "tinygltfloader"
    version = "0.9.2"
    description = "Header-only C++ glTF 1.x parser"
    license = "MIT"
    homepage = "https://github.com/syoyo/tinygltfloader"
    url = "https://github.com/syoyo/tinygltfloader"

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

        # The upstream Makefile hard-codes g++; use Conan's host compiler
        # instead so the OHOS clang++ profile is honored (R33).
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compiler_executables.get("cpp", "clang++")
        test_source = os.path.join(self.source_folder, "test.cc")
        test_binary = os.path.join(self.build_folder, "loader_test")
        fixture = os.path.join(self.source_folder, "box.gltf")
        self.run(
            f'"{cxx}" -Wall -Werror -g -O2 "{test_source}" '
            f'-o "{test_binary}"'
        )
        self.run(f'"{test_binary}" "{fixture}"')

    def package(self):
        for header in ("tiny_gltf_loader.h", "picojson.h", "stb_image.h"):
            copy(
                self,
                header,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "include"),
            )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "tinygltfloader")
        self.cpp_info.set_property(
            "cmake_target_name", "tinygltfloader::tinygltfloader"
        )
