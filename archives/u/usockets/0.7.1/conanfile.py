#!/usr/bin/env python3
"""Conan recipe for usockets 0.7.1 — cross-platform async networking C library.
uSockets is the low-level event-loop engine behind uWebSockets.
Build system: pure Makefile (no configure, no make install).
Output: uSockets.a static library + libusockets.h header.
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UsocketsConan(ConanFile):
    name = "usockets"
    version = "0.7.1"
    description = "Cross-platform asynchronous networking C library (uWebSockets engine)"
    license = "Apache-2.0"
    homepage = "https://github.com/uNetworking/uSockets"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"
        ar = comp_execs.get("ar") or "llvm-ar"
        openssl = self.dependencies["openssl"].cpp_info
        openssl_includes = " ".join(f"-I{d}" for d in openssl.includedirs)
        self.run(
            f'make CC="{cc}" CXX="{cxx}" AR="{ar}" '
            f'CFLAGS="{openssl_includes}" WITH_OPENSSL=1 -j1',
            cwd=self.source_folder
        )

    def package(self):
        copy(self, "libusockets.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "uSockets.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        os.rename(
            os.path.join(self.package_folder, "lib", "uSockets.a"),
            os.path.join(self.package_folder, "lib", "libuSockets.a")
        )

    def package_info(self):
        self.cpp_info.libs = ["uSockets"]
        self.cpp_info.system_libs = ["stdc++"]
