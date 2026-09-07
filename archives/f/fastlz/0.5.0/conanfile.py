#!/usr/bin/env python3
"""Conan recipe — fastlz 0.5.0 (byte-aligned LZ77 compression library).

Build system: no top-level Makefile — the library is a single source file
fastlz.c + fastlz.h, compiled directly. R33: compiler obtained from Conan
conf, never from raw shell variables.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FastlzConan(ConanFile):
    name = "fastlz"
    version = "0.5.0"
    description = "FastLZ - Byte-aligned LZ77 compression library"
    license = "MIT"
    homepage = "https://github.com/ariya/FastLZ"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # fastlz has no top-level Makefile: compile the single C file directly.
        # R33: compiler obtained from Conan conf (dict form), never raw shell vars.
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp.get("c", "clang")
        ar = comp.get("ar", "llvm-ar")
        src = os.path.join(self.source_folder, "fastlz.c")
        if self.options.shared:
            self.run(f"{cc} -O2 -fPIC -shared -o libfastlz.so {src}", cwd=self.source_folder)
        else:
            self.run(f"{cc} -O2 -fPIC -c {src} -o fastlz.o", cwd=self.source_folder)
            self.run(f"{ar} rcs libfastlz.a fastlz.o", cwd=self.source_folder)

    def package(self):
        copy(self, "fastlz.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libfastlz.so*", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libfastlz.a", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["fastlz"]