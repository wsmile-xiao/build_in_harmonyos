#!/usr/bin/env python3
"""Conan recipe for mujs 1.3.5 — Makefile build.

MuJS is a lightweight embeddable Javascript interpreter (C99, Makefile build).
- Build: make release HAVE_READLINE=no prefix=<prefix> -j1
- Install: make install HAVE_READLINE=no prefix=<prefix> DESTDIR=<staging>
- Produces: bin/mujs, bin/mujs-pp (CLI tools), lib/libmujs.a, lib/libmujs.so,
  include/mujs.h, lib/pkgconfig/mujs.pc
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MujsConan(ConanFile):
    name = "mujs"
    version = "1.3.5"
    description = "MuJS embeddable Javascript interpreter"
    license = "ISC"
    homepage = "https://mujs.com/"
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
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        # R33: compiler/flags come from Conan conf, never bare shell ${CC}
        # mujs Makefile must run from the source dir (no configure step)
        self.run(f"make release HAVE_READLINE=no CC={cc} AR={ar} -j1", cwd=self.source_folder)

    def package(self):
        apply_conandata_patches(self)
        # Use the upstream install target with DESTDIR staging (R5-style isolation)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        staging = os.path.join(self.build_folder, "stage")
        self.run(f"make install HAVE_READLINE=no CC={cc} AR={ar} "
                 f"DESTDIR={staging} -j1", cwd=self.source_folder)
        copy(self, "*", os.path.join(staging, "usr", "local"), self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["mujs"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "mujs")
