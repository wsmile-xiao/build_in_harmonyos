#!/usr/bin/env python3
"""Conan recipe — libbig_int 2.6 (portable arbitrary-length integer & bitset C library).

Upstream: https://github.com/mlafeldt/libbig_int (official master HEAD
fd8f3278ea03eb849420aa5eab540319ff9b3846, upstream has no 2.6 tag; version 2.6
is the task-designated version for this archive).

Upstream build: CMake `PROJECT("libbig_int" C)` with ADD_LIBRARY(big_int).
Upstream CMakeLists.txt installs only the static library to `lib/` and does NOT
install headers — patched (0001) to install include/ into include/ so consumers
can include big_int.h. CMAKE_C_FLAGS hardcodes "-Wall -Werror -O2"; the recipe
lets the Conan OHOS toolchain drive flags while keeping upstream warnings
(no -Werror, see 0002) to avoid hard failure on newer clang diagnostics.

Library name: big_int -> libbig_int.a (static by default, R26-style safe for
non-system-named lib; consumers link via Conan).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class LibbigIntConan(ConanFile):
    name = "libbig_int"
    version = "2.6"
    description = ("Portable C library to calculate integers and bitsets of "
                   "arbitrary length (from the big_int PHP library by Alexander Valyalkin)")
    license = "MIT"  # LICENSE is MIT-style
    homepage = "https://github.com/mlafeldt/libbig_int"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("bignum", "bitset", "arbitrary-precision", "c")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility — use `in ("Linux", "OHOS")`
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["big_int"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
