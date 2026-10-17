#!/usr/bin/env python3
"""Conan recipe for snow 20130616 — Whitespace steganography tool (Makefile)."""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SnowConan(ConanFile):
    name = "snow"
    version = "20130616"
    description = "Whitespace steganography: coded messages using whitespace"
    license = "Apache-2.0"
    homepage = "https://darkside.com.au/snow/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf (profile), never from shell env vars
        # or hardcoded "clang" fallback (would silently produce wrong-arch
        # binaries on workers where CC isn't exported).
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "No C compiler configured: set "
                "tools.build:compiler_executables in the Conan profile."
            )
        self.run(f"make CC={cc}", cwd=self.source_folder)

    def package(self):
        self.run(f"install -d {self.package_folder}/bin")
        self.run(f"install -m 755 snow {self.package_folder}/bin/", cwd=self.source_folder)
        self.run(f"install -d {self.package_folder}/man/man1")
        self.run(f"install -m 644 snow.1 {self.package_folder}/man/man1/", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []