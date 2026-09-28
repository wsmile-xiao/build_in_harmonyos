#!/usr/bin/env python3
"""Conan 2.x recipe for tiny-aes-c — small portable AES128/192/256 in C.

Upstream: https://github.com/kokke/tiny-AES-c (v1.0.0 tag, The Unlicense).
Build system: CMake (single static library target `tiny-aes` from aes.c).
Mode macros (AES128/AES192/AES256, CBC/ECB/CTR) default to AES128 + all
three modes in aes.h; the upstream CMakeLists.txt does not pass explicit
macros, so defaults are used as-is to stay byte-identical to upstream.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
import os


class TinyAesCConan(ConanFile):
    name = "tiny-aes-c"
    version = "1.0.0"
    description = "Small portable AES128/192/256 encryption in C (ECB/CBC/CTR)"
    license = "Unlicense"
    homepage = "https://github.com/kokke/tiny-AES-c"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMakeLists.txt has no install() rules; copy artifacts directly.
        copy(self, "libtiny-aes.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "aes.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "aes.hpp", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "unlicense.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tiny-aes"]
