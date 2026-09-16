#!/usr/bin/env python3
"""Conan recipe — mpreal 3.7.1 (header-only C++ wrapper for MPFR).

mpreal.h is a single-header C++ interface to MPFR (itself built on GMP).
No library artifact is compiled or installed: the header is copied into
the consumer's include path, and all arbitrary-precision arithmetic is
provided by the mpfr/4.2.2.1 dependency (which brings gmp/6.3.0).
Upstream ships no test suite — the repo contains only mpreal.h, a demo
example/ (example.cpp + plain makefile) and docs — so R51 upstream tests
= 0 and the verification burden is carried by the real consumer test in
test_package/ (R34: compiles against the installed header, links
libmpfr/libgmp, asserts computed values and executes on device).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MprealConan(ConanFile):
    name = "mpreal"
    version = "3.7.1"
    description = "C++ wrapper class for the MPFR arbitrary-precision floating-point library"
    license = "MIT"
    homepage = "https://github.com/advanpix/mpreal"
    url = "https://github.com/advanpix/mpreal"
    topics = ("mpfr", "gmp", "bignum", "header-only", "arbitrary-precision")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mpfr/4.2.2.1")

    def package_id(self):
        self.info.clear()

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"mpreal not validated for {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Header-only: no build toolchain is consumed by the recipe itself,
        # but generate() is mandatory so consumers always get a complete
        # toolchain environment (utf8.h 教训: 漏写导致 CMakePresets 缺失).
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Header-only: no library artifact to compile. The upstream makefile
        # only builds a demo program and there is no test suite to run (R51: 0).

    def package(self):
        copy(self, "mpreal.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "copying.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
