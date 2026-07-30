#!/usr/bin/env python3
"""Conan recipe for libsass — Sass/SCSS compiler written in C/C++.

libsass uses a plain Makefile (no configure script).
Build: make
Install: make install install-headers PREFIX=... DESTDIR=...
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibsassConan(ConanFile):
    name = "libsass"
    version = "3.6.5"
    description = "Sass/SCSS compiler written in C/C++ (libsass)"
    license = "MIT"
    homepage = "https://sass-lang.com/libsass"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain generates CC/CXX/CFLAGS/CXXFLAGS env vars
        # from the Conan profile, which libsass's Makefile respects via ?=
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # libsass has no configure script; run make in source dir
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Pre-create directories since Makefile uses mkdir without -p
        prefix = self.package_folder
        os.makedirs(os.path.join(prefix, "lib"), exist_ok=True)
        os.makedirs(os.path.join(prefix, "include"), exist_ok=True)
        os.makedirs(os.path.join(prefix, "include", "sass"), exist_ok=True)
        # Install static lib and headers from source dir
        self.run(
            'make install install-headers PREFIX="{}" DESTDIR=""'.format(prefix),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package_info(self):
        # Library file is libsass.a → linker name is "sass" (strip lib prefix)
        self.cpp_info.libs = ["sass"]
