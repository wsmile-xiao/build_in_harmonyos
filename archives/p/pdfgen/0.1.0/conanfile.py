#!/usr/bin/env python3
"""Conan recipe — pdfgen 0.1.0

PDFGen is a simple C library for creating PDF files (public domain,
unlicense). The whole library is a single compilation unit (pdfgen.c +
pdfgen.h) with zero external dependencies. The recipe drives a minimal
CMake project that compiles the single translation unit and archives
libpdfgen.a; the toolchain (compiler + ar) is selected entirely by the
Conan CMakeToolchain from the profile (R33: no bare shell env vars).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy


class PdfGenConan(ConanFile):
    name = "pdfgen"
    version = "0.1.0"
    description = "Simple C library for creating PDF files (single source file, zero dependencies)"
    license = "Unlicense"
    homepage = "https://github.com/AndreRenaud/PDFGen"
    url = "https://github.com/AndreRenaud/PDFGen"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "fPIC": [True, False],
        "shared": [True, False],
    }
    default_options = {
        "fPIC": True,
        # static by default: leaf library, avoids polluting /lib with a
        # same-named .so (R26 spirit)
        "shared": False,
    }

    implements = ["auto_shared_fpic"]

    exports_sources = "CMakeLists.txt", "patches/*"

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: flags/toolchain come from the Conan toolchain, never from
        # bare shell env vars.
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "pdfgen")
        self.cpp_info.set_property("cmake_target_name", "pdfgen::pdfgen")
        self.cpp_info.libs = ["pdfgen"]
        self.cpp_info.includedirs = ["include"]
