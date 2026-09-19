#!/usr/bin/env python3
"""Conan recipe — igloo 1.1.1 (header-only C++ unit testing framework).

Igloo is a header-only library: upstream CMakeLists.txt only builds the
self-test binaries (igloo-tests / snowhouse-tests); there is no library
artifact to compile/link. This recipe therefore packages the public
headers as a header-only Conan package and runs the upstream self-tests
as a compile-check gate inside build() (skipped for consumers via the
`with_tests` option, default off for CI consumers).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class IglooConan(ConanFile):
    name = "igloo"
    version = "1.1.1"
    description = "igloo - A framework for unit testing in C++"
    license = "BSL-1.0"
    homepage = "https://igloo-testing.org/"
    url = "https://github.com/joakimkarlsson/igloo"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"with_tests": [True, False]}
    default_options = {"with_tests": False}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix invalid UTF-8 byte (0xE4) in upstream copyright comment; clang 15
        # with -Werror -Winvalid-utf8 rejects it when consumers compile with Werror.
        # Done here (byte-level, latin-1) instead of patches/ because refresh-patch
        # dry-run cannot represent the invalid byte and would drop the patch.
        utf8_hdr = os.path.join(self.source_folder, "igloo", "external", "snowhouse",
                                "snowhouse", "fluent", "operators", "collections",
                                "collectionconstraintevaluator.h")
        if os.path.exists(utf8_hdr):
            replace_in_file(self, utf8_hdr, "Kim Gr\u00e4sman", "Kim Gr\u00c3\u00a4sman",
                            strict=False, encoding="latin-1")
        if self.options.with_tests:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
    def package(self):
        inc = os.path.join(self.package_folder, "include")
        copy(self, "LICENSE_1_0.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder, keep_path=False)
        copy(self, "igloo/*.h", dst=inc, src=self.source_folder)
        copy(self, "igloo/core/*.h", dst=inc, src=self.source_folder)
        copy(self, "igloo/core/outputters/*.h", dst=inc, src=self.source_folder)
        copy(self, "igloo/core/testlisteners/*.h", dst=inc, src=self.source_folder)
        copy(self, "igloo/external/snowhouse/snowhouse/*.h", dst=inc, src=self.source_folder)
        copy(self, "igloo/external/snowhouse/snowhouse/*/*.h", dst=inc, src=self.source_folder)
        copy(self, "igloo/external/snowhouse/snowhouse/*/*/*.h", dst=inc, src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []