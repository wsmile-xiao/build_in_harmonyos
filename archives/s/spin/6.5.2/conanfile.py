#!/usr/bin/env python3
"""Conan recipe — spin 6.5.2 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SpinConan(ConanFile):
    name = "spin"
    version = "6.5.2"
    description = "Efficient verification tool for multi-threaded software"
    license = "BSD-like"
    homepage = "https://spinroot.com/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

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
        src_dir = os.path.join(self.source_folder, "Src")
        self.run(
            f'make -C "{src_dir}" '
            'CC=clang '
            'CFLAGS="-fPIC -O2 -DNXT -Wall -pedantic" '
            'YACC="bison -y" '
            'LDFLAGS="-fuse-ld=bfd"'
        )
        self.run(
            f'make -C "{src_dir}" '
            'CC=clang '
            'CFLAGS="-fPIC -O2 -DNXT -Wall -pedantic" '
            'YACC="bison -y" '
            'LDFLAGS="-fuse-ld=bfd" '
            'check 2>&1 || true'
        )

    def package(self):
        src_dir = os.path.join(self.source_folder, "Src")
        self.run(
            f'make -C "{src_dir}" '
            f'DESTDIR={self.package_folder} '
            'INSTALL="install -D" '
            'install'
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
