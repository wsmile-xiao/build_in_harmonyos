#!/usr/bin/env python3
"""Conan recipe — libkeccak 1.4.3 (Keccak/SHA-3/SHAKE/cSHAKE/HMAC library).

Build system: POSIX Makefile (no configure script).
config.mk defaults CC=c99, which does not exist on HarmonyOS, so CC/AR are
passed on the command line from the Conan toolchain (R33).
Packaging uses copy() instead of `make install` to skip man pages and the
`ln -sf` install rules (HMDFS does not allow overwriting symlinks).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibkeccakConan(ConanFile):
    name = "libkeccak"
    version = "1.4.3"
    description = "Keccak-family hashing library (SHA-3, SHAKE, cSHAKE, RawSHAKE, HMAC)"
    license = "ISC"
    homepage = "https://github.com/maandree/libkeccak"

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
        # R33: compiler from Conan conf, never from shell env vars
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        cc = executables.get("c", "clang")
        ar = executables.get("ar", "ar")
        # Upstream Makefile: `libkeccak.a` (static) / `libkeccak.so` (shared,
        # soname libkeccak.so.1). The .c.o rule always compiles with -fPIC.
        target = "libkeccak.so" if self.options.shared else "libkeccak.a"
        self.run(f'make -j1 CC="{cc}" AR="{ar}" {target}', cwd=self.source_folder)

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libkeccak.h", src=self.source_folder, dst=include_dir)
        copy(self, "*.h", src=os.path.join(self.source_folder, "libkeccak"),
             dst=os.path.join(include_dir, "libkeccak"))

        if self.options.shared:
            copy(self, "libkeccak.so", src=self.source_folder, dst=lib_dir)
            # Reproduce the upstream soname layout:
            #   libkeccak.so -> libkeccak.so.1 -> libkeccak.so.1.4
            real_lib = os.path.join(lib_dir, "libkeccak.so.1.4")
            os.rename(os.path.join(lib_dir, "libkeccak.so"), real_lib)
            for link_name in ("libkeccak.so.1", "libkeccak.so"):
                link_path = os.path.join(lib_dir, link_name)
                # HMDFS: `ln -sf` cannot overwrite, always remove first
                if os.path.islink(link_path) or os.path.exists(link_path):
                    os.remove(link_path)
                os.symlink("libkeccak.so.1.4", link_path)
        else:
            copy(self, "libkeccak.a", src=self.source_folder, dst=lib_dir)

    def package_info(self):
        self.cpp_info.libs = ["keccak"]
