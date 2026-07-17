#!/usr/bin/env python3
"""Conan recipe for duktape 2.7.0 — embedded JavaScript engine.

Duktape uses a custom Makefile.sharedlibrary (not autotools/cmake).
Build produces:
  - libduktape.a / libduktape.so  (library)
  - duk                           (command-line JS interpreter)
  - duktape.h, duk_config.h       (headers)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DuktapeConan(ConanFile):
    name = "duktape"
    version = "2.7.0"
    description = "Embedded ECMAScript (JavaScript) engine for C/C++ applications"
    license = "MIT"
    homepage = "https://duktape.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take toolchain paths from Conan conf, never from shell env.
        # The profile registers tools.build:compiler_executables as a *dict*
        # ({c, cpp}); the `:c`/`:ar` sub-key form is NOT a registered conf.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        if self.options.shared:
            # Build shared library using Makefile.sharedlibrary
            self.run(f'make -f Makefile.sharedlibrary CC="{cc}" '
                     f'INSTALL_PREFIX={self.package_folder} '
                     f'CFLAGS="-fPIC -O2" -j1',
                     cwd=self.source_folder)
        else:
            # Build static library by compiling the single-file source
            self.run(f'"{cc}" -O2 -fPIC -c src/duktape.c -Isrc -o duktape.o',
                     cwd=self.source_folder)
            self.run(f'"{ar}" rcs libduktape.a duktape.o',
                     cwd=self.source_folder)
            self.run(f'"{ranlib}" libduktape.a',
                     cwd=self.source_folder)

        # Build duk command-line tool (with print/alert and console support)
        self.run(
            f'"{cc}" -DDUK_CMDLINE_PRINTALERT_SUPPORT -DDUK_CMDLINE_CONSOLE_SUPPORT '
            f'-Isrc -I./examples/cmdline -I./extras/print-alert -I./extras/console '
            f'-Wall -Wextra -Os -o duk '
            f'./examples/cmdline/duk_cmdline.c '
            f'./extras/print-alert/duk_print_alert.c '
            f'./extras/console/duk_console.c '
            f'-L. -lduktape -lm',
            cwd=self.source_folder)

    def package(self):
        # Install headers
        copy(self, "duktape.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "duk_config.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))

        # Install libraries
        if self.options.shared:
            copy(self, "libduktape.so*", self.source_folder,
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libduktape.a", self.source_folder,
                 os.path.join(self.package_folder, "lib"))

        # Install duk command-line tool
        copy(self, "duk", self.source_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["duktape"]
        self.cpp_info.bindirs = ["bin"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["m"]
