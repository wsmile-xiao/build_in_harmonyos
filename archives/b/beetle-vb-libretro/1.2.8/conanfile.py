#!/usr/bin/env python3
"""Conan recipe — beetle-vb-libretro 1.2.8 (libretro core, plain Makefile).

Standalone hard fork of Mednafen VB to libretro (Nintendo Virtual Boy emulator
core). The upstream build is a plain Makefile producing a shared plugin
mednafen_vb_libretro.so loaded by libretro frontends via dlopen.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BeetlevblibretroConan(ConanFile):
    name = "beetle-vb-libretro"
    version = "1.2.8"
    description = "Standalone hard fork of Mednafen VB to libretro (Virtual Boy emulator core)"
    license = "GPL-2.0"
    homepage = "https://github.com/libretro/beetle-vb-libretro"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Plain Makefile (no configure). The Makefile lives in the source
        # folder (basic_layout keeps build-release empty), so run make there.
        # CC/CXX resolve from the OHOS profile buildenv PATH
        # (/data/service/hnp/bin). -j1 avoids jobserver issues on
        # constrained CI workers.
        self.run("make CC=clang CXX=clang++ -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "mednafen_vb_libretro.so", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "libretro.h",
             os.path.join(self.source_folder, "libretro-common", "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", self.source_folder, self.package_folder)

    def package_info(self):
        # Libretro cores are dlopen'ed by exact filename by frontends; the
        # public consumer surface is libretro.h + the retro_* ABI exported
        # by the plugin.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
