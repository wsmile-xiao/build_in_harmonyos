#!/usr/bin/env python3
"""Conan recipe for zlib 1.3.1.1.1.

This suffix release keeps zlib static-only to avoid colliding with the system
libz.so, but builds libz.a from PIC objects so consumers may link it into DSOs
or Python extension modules.
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZlibConan(ConanFile):
    name = "zlib"
    version = "1.3.1.1.1"
    description = "Massively-used data compression library (DEFLATE/inflate)."
    license = "Zlib"
    homepage = "https://zlib.net/"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "static-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cflags = os.environ.get("CFLAGS", "-O3")
        if "-fPIC" not in cflags.split():
            cflags = f"{cflags} -fPIC"

        self.run(
            f'CONFIG_SHELL="{config_shell}" CC="{cc}" CFLAGS="{cflags}" '
            f'"{config_shell}" ./configure --static --prefix=/'
        )
        self.run("make -j1")
        self.run("make check")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["z"]
        self.cpp_info.set_property("pkg_config_name", "zlib")
        self.cpp_info.set_property("cmake_file_name", "zlib")
        self.cpp_info.set_property("cmake_target_name", "zlib::zlib")
