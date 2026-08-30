#!/usr/bin/env python3
"""Conan recipe for cppcodec 0.2 — header-only C++ encoding library.

cppcodec is a header-only library (base64/base64url/base32/base32hex/hex).
No compilation is needed. The recipe downloads the source and copies the
`cppcodec/` header tree plus the pkg-config file into the package.

Upstream tests (Catch2 suite under test/) are compiled and run in
test_package/test() to provide HMBS verification evidence.
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CppcodecConan(ConanFile):
    name = "cppcodec"
    version = "0.2"
    description = "C++ header-only library to encode/decode base64, base64url, base32, base32hex and hex"
    license = "MIT"
    homepage = "https://github.com/tplgy/cppcodec"
    url = ""

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no compilation needed for the library itself.
        # Upstream Catch2 tests are compiled and run in test_package/test()
        # (see test_package/conanfile.py) because that lifecycle hook always
        # executes on every ``conan create`` regardless of binary cache state.
        pass

    def package(self):
        # Copy the header tree (cppcodec/*.hpp including data/ and detail/).
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "cppcodec"),
             dst=os.path.join(self.package_folder, "include", "cppcodec"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cppcodec")
        self.cpp_info.set_property("cmake_target_name", "cppcodec::cppcodec")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link.
        self.cpp_info.libs = []
