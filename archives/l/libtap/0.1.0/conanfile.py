#!/usr/bin/env python3
"""Conan recipe for libtap — Test Anything Protocol library for C."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibtapConan(ConanFile):
    name = "libtap"
    version = "0.1.0"
    description = "Write tests in C using the Test Anything Protocol"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/zorgnax/libtap"
    url = ""

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

        # R33: Get compiler from Conan conf (dict), never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        if self.options.shared:
            self.run(f"make -C {self.source_folder} CC={cc} AR={ar} RANLIB={ranlib} libtap.so -j1")
        else:
            self.run(f"make -C {self.source_folder} CC={cc} AR={ar} RANLIB={ranlib} libtap.a -j1")

    def package(self):
        copy(self, "tap.h", self.source_folder, os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libtap.so", self.source_folder, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libtap.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["tap"]
