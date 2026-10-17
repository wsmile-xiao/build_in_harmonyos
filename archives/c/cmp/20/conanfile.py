#!/usr/bin/env python3
"""Conan recipe for cmp 20 (camgunz/cmp — C MessagePack implementation).

cmp has no build system ("There is no build system for CMP", README):
the library is cmp.c + cmp.h. We compile cmp.c into a static library and
install the header, which is the only packaging needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.build import cross_building


class CmpConan(ConanFile):
    name = "cmp"
    version = "20"
    description = "C MessagePack implementation (cmp by camgunz)"
    license = "MIT"
    homepage = "https://github.com/camgunz/cmp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL has no extension; force a .tar.gz filename so conan's
        # archive detection (get) unpacks it correctly.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="cmp-20.tar.gz")

    def build(self):
        apply_conandata_patches(self)
        # Direct clang compile of the single source file (no build system).
        # R33: compiler must come from the Conan toolchain env, never bare
        # shell variables like ${CC}.
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "-O2")
        src = self.source_folder
        build = self.build_folder
        self.run(f"{cc} {cflags} -std=c89 -Wno-c99-extensions -I{src} "
                 f"-c {src}/cmp.c -o {build}/cmp.o")
        self.run(f"llvm-ar rcs {build}/libcmp.a {build}/cmp.o")

    def package(self):
        # copy() semantics: src is a DIR, pattern matches inside it;
        # dst must be an explicit absolute package path.
        copy(self, "libcmp.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "cmp.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["cmp"]
