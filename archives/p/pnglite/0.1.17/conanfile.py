#!/usr/bin/env python3
"""Conan recipe for pnglite 0.1.17."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)


class PngliteConan(ConanFile):
    name = "pnglite"
    version = "0.1.17"
    description = "A lightweight C library for reading and writing PNG images"
    license = "Zlib"
    homepage = "https://sourceforge.net/projects/pnglite/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}
    exports_sources = "CMakeLists.txt", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)
        # The official zip stores its two source files with CRLF endings.
        # Normalize them so repository-standard LF patches apply reproducibly.
        for filename in ("pnglite.c", "pnglite.h"):
            path = os.path.join(self.source_folder, filename)
            content = load(self, path).replace("\r\n", "\n").replace("\r", "\n")
            save(self, path, content)

    def generate(self):
        dependencies = CMakeDeps(self)
        dependencies.generate()
        toolchain = CMakeToolchain(self)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["pnglite"]
        self.cpp_info.requires = ["zlib::zlib"]
