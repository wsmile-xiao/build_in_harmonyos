#!/usr/bin/env python3
"""Conan recipe for libgsm 1.0.18 — GSM 06.10 speech codec library.

Build system: raw Makefile (no configure script).
The Makefile patch adapts: CC→clang, DESTDIR/PREFIX support, hard links→symlinks.
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibgsmConan(ConanFile):
    name = "libgsm"
    version = "1.0.18"
    description = "GSM 06.10 speech codec library for audio compression"
    license = "custom"
    homepage = "http://kbs.cs.tu-berlin.de/~jutta/gsm/"
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
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Do not rely on shell env vars (CC/AR/RANLIB).
        # The Makefile patch sets CC=clang and CCFLAGS with --target=aarch64-linux-ohos.
        # R9: Always use -j1
        self.run(f"make -C {self.source_folder} -j1")

    def package(self):
        # Copy library (lib/libgsm.a → lib/)
        copy(self, "libgsm.a", os.path.join(self.source_folder, "lib"),
             os.path.join(self.package_folder, "lib"))
        # Copy header (inc/gsm.h → include/)
        copy(self, "gsm.h", os.path.join(self.source_folder, "inc"),
             os.path.join(self.package_folder, "include"))
        # Copy binaries (bin/toast → bin/)
        copy(self, "toast", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["gsm"]
