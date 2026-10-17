#!/usr/bin/env python3
"""Conan recipe — libdumbtts (raw Makefile project, no configure).

libdumbtts extends "dumb synthesizers" with multilingual character
pronunciation / transliteration. Pure C library. Upstream ships a plain
Makefile under src/ (no configure script), installs with DESTDIR support.

Adaptation notes:
  - GNU C nested functions (gcc extension) are hoisted to file scope in
    patches/*.patch because the OHOS toolchain is clang 15 which lacks
    nested-function support.
  - Upstream Makefile only enables -fPIC on x86_64; OHOS runs on aarch64
    (armv8) and shared libs require -fPIC, forced here via PIC=-fPIC.
  - Compiler/flag variables are taken from Conan conf/toolchain, never
    from shell environment (R33).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibdumbttsConan(ConanFile):
    name = "libdumbtts"
    version = "0.3.2"
    description = "Library extending capabilities of dumb synthesizers (TTS helper)"
    license = "LGPL-2.1-or-later"
    homepage = "http://www.polip.com/"
    url = "https://www.polip.com/files/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # stdlib-only, zero third-party deps

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler/flag variables come from Conan conf, never shell env.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c", "clang")
        # Upstream Makefile uses the variable `C` for the compiler and only
        # adds -fPIC on x86_64; aarch64 shared libs need explicit -fPIC.
        # basic_layout puts cwd in build-release/, so run make in source dir.
        self.run(f"make -C src C={cc} PIC=-fPIC -j1", cwd=self.source_folder)

    def package(self):
        src_d = os.path.join(self.source_folder, "src")
        copy(self, "libdumbtts.so*", src_d, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "libdumbtts.h", src_d, os.path.join(self.package_folder, "include"), keep_path=False)
        # Language config data (pronunciation dictionaries) shipped for
        # run-time deployment under <prefix>/etc/dumbtts or ~/.dumbtts_xx.conf
        copy(self, "*.conf", os.path.join(self.source_folder, "conf"), os.path.join(self.package_folder, "res", "dumbtts"), keep_path=False)
        copy(self, "*.dic", os.path.join(self.source_folder, "conf"), os.path.join(self.package_folder, "res", "dumbtts"), keep_path=False)
        # soname symlink chain: libdumbtts.so -> libdumbtts.so.0 -> libdumbtts.so.0.3.1
        lib_d = os.path.join(self.package_folder, "lib")
        so_main = os.path.join(lib_d, "libdumbtts.so")
        so_0 = os.path.join(lib_d, "libdumbtts.so.0")
        so_full = os.path.join(lib_d, "libdumbtts.so.0.3.1")
        if os.path.isfile(so_full):
            if not os.path.lexists(so_0):
                os.symlink("libdumbtts.so.0.3.1", so_0)
            if not os.path.lexists(so_main):
                os.symlink("libdumbtts.so.0", so_main)

    def package_info(self):
        self.cpp_info.libs = ["dumbtts"]