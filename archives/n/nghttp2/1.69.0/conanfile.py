#!/usr/bin/env python3
"""Conan recipe for nghttp2 1.69.0 — HTTP/2 C Library and tools.

Builds the full library + applications (nghttp, nghttpd, nghttpx, h2load)
and HPACK tools (inflatehd, deflatehd) for HarmonyOS PC (aarch64).

Compatibility: OHOS libc++ (LLVM 15) has partial C++20 ranges support.
The ranges_compat.h header provides missing std::ranges algorithms.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class Nghttp2Conan(ConanFile):
    name = "nghttp2"
    version = "1.69.0"
    description = "HTTP/2 C Library and tools"
    license = "MIT"
    homepage = "https://github.com/nghttp2/nghttp2"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_applications": [True, False],
    }
    default_options = {
        "shared": True,
        "with_applications": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # Export ranges_compat.h as a source file
        copy(self, "ranges_compat.h", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("zlib/1.3.2")
        self.requires("openssl/3.5.6.1.1")
        if self.options.with_applications:
            self.requires("libev/4.33")
            self.requires("jansson/2.15.1.1")
            self.requires("c-ares/1.34.6")

    def build_requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_LIB_ONLY"] = "OFF"
        if self.options.with_applications:
            tc.variables["ENABLE_APP"] = "ON"
            tc.variables["ENABLE_HPACK_TOOLS"] = "ON"
        else:
            tc.variables["ENABLE_APP"] = "OFF"
            tc.variables["ENABLE_HPACK_TOOLS"] = "OFF"
        tc.variables["ENABLE_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        # Copy ranges_compat.h to source dir
        copy(self, "ranges_compat.h", self.recipe_folder, self.source_folder)
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["nghttp2"]
        self.cpp_info.set_property("cmake_file_name", "nghttp2")
        self.cpp_info.set_property("cmake_target_name", "nghttp2::nghttp2")
        if self.options.shared:
            self.cpp_info.defines = ["NGHTTP2_DLL"]
