#!/usr/bin/env python3
"""Conan recipe — strcase 0.1 (header-only C library, VirtualSquare).

strcase.h implements multiway branch (switch) for short strings in C:
STRCASE(...) builds compile-time case labels from comma-separated
characters; strcase()/strcase_tolower() are static inline runtime
conversions. The whole library is one header — nothing is compiled.
Upstream ships no test suite, so the consumer test in test_package/
carries the verification (real API calls, assertions, runs on device).
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


class StrcaseConan(ConanFile):
    name = "strcase"
    version = "0.1"
    description = "Multiway branch (switch) for short strings in C (one header file)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rd235/strcase"
    url = ""  # CI fills this
    topics = ("switch", "string", "header-only", "macro")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"strcase not validated for {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Header-only: no build toolchain consumed by the recipe itself,
        # but generate() is mandatory so consumers always get a complete
        # toolchain environment (utf8.h 教训: 漏写导致 CMakePresets 缺失).
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Header-only: no artifact to compile; upstream has no test suite (R51: 0).

    def package(self):
        copy(self, "strcase.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
