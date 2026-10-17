#!/usr/bin/env python3
"""Conan recipe — libok 0.6.5 (plain Makefile).

libok is a tiny TAP (Test Anything Protocol) output library by Joseph
Werle, published via clib/npm and built with a plain Makefile
(no configure/autotools). It produces a static archive libok.a and a
shared libok.so.0.6. Header ok.h contains the full implementation behind
LIBOK_INCLUDE_IMPLEMENTATION; ok.c just includes it.

Build notes:
- No configure step: build() runs `make all` directly with CC/CFLAGS
  taken from the Conan toolchain (R33: no undefined shell env vars).
- Install is done manually in package() (the upstream `make install`
  uses a non-standard PREFIX/DESTDIR layout), copying ok.h to include/
  and the libs to lib/.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibokConan(ConanFile):
    name = "libok"
    version = "0.6.5"
    description = "Super tiny TAP output library"
    license = "MIT"
    homepage = "https://github.com/jwerle/libok"
    url = "https://github.com/jwerle/libok"

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
        # Compiler/flags come from the Conan toolchain conf (R33).
        comp = self.conf.get("tools.build:compiler_executables",
                             check_type=dict, default={})
        cc = comp.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "libok requires tools.build:compiler_executables[c] from the "
                "Conan toolchain (R33); no shell-fallback compiler allowed")
        cflags = self.conf.get("tools.build:cflags", default=["-fPIC -O2"])
        cflags_str = " ".join(cflags) if isinstance(cflags, list) else str(cflags)
        # Rebuild from clean to guarantee reproducibility.
        self.run("make clean", cwd=self.source_folder, env="conanbuild")
        self.run(f"make all CC='{cc}' CFLAGS='{cflags_str}'",
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "ok.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libok.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libok.so*",
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["ok"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
