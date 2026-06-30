#!/usr/bin/env python3
"""Conan recipe — tbox 1.8.0 (xmake.sh build system)

tbox uses xmake.sh (a shell-based configure script) that generates a Makefile
in the source directory. This recipe enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TboxConan(ConanFile):
    name = "tbox"
    version = "1.8.0"
    description = "Glib-like multi-platform C library"
    license = "Apache-2.0"
    homepage = "https://github.com/tboox/tbox"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF)
        # tbox builds static library by default; configure uses CC/CXX from env
        pass

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # xmake.sh configure script generates Makefile in source dir
        # Use --prefix=/usr/local for standard layout (R1: parameter minimization)
        self.run(f"cd {src} && chmod +x configure && ./configure --prefix=/usr/local")
        # Use -j1 to avoid HarmonyOS jobserver mkfifo limitation (E051)
        self.run(f"make -C {src} -j1")

    def package(self):
        src = self.source_folder
        # Install to temp dir, then copy to package folder in standard Conan layout
        tmp_install = os.path.join(self.build_folder, "tbox_install")
        self.run(f"make -C {src} install DESTDIR={tmp_install}")
        # Copy library
        copy(self, "libtbox.a",
             src=os.path.join(tmp_install, "usr", "local", "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        # Copy headers (public headers only, as installed by make install)
        copy(self, "*.h",
             src=os.path.join(tmp_install, "usr", "local", "include", "tbox"),
             dst=os.path.join(self.package_folder, "include", "tbox"))
        # Copy assembly headers
        copy(self, "*.S",
             src=os.path.join(tmp_install, "usr", "local", "include", "tbox"),
             dst=os.path.join(self.package_folder, "include", "tbox"))

    def package_info(self):
        self.cpp_info.libs = ["tbox"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
