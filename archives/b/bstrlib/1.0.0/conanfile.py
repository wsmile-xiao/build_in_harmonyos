#!/usr/bin/env python3
"""Conan recipe — bstrlib 1.0.0 (Better String Library).

Upstream ships plain C sources (no configure / Makefile), so this recipe
builds the static/shared library directly with the Conan-managed compiler.
Core sources: bstrlib.c + bstraux.c + bsafe.c + buniutil.c + utf8util.c.
C++ wrapper bstrwrap is not built here; the C API is the primary interface.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BstrlibConan(ConanFile):
    name = "bstrlib"
    version = "1.0.0"
    description = "The Better String Library — a safe, portable C string library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/websnarf/bstrlib"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _sources = ["bstrlib.c", "bstraux.c", "bsafe.c", "buniutil.c", "utf8util.c"]
    _headers = ["bstrlib.h", "bstraux.h", "bsafe.h", "buniutil.h", "utf8util.h"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler/flags from Conan conf, never bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"
        flags = self.conf.get("tools.build:cflags", default=[], check_type=list)
        flags = flags + ["-O2", "-fPIC"]
        objs = []
        for src in self._sources:
            obj = os.path.join(self.build_folder, os.path.splitext(src)[0] + ".o")
            self.run(f'{cc} {" ".join(flags)} -c {os.path.join(self.source_folder, src)} -o {obj}')
            objs.append(obj)
        if self.options.shared:
            self.run(f'{cc} -shared {" ".join(objs)} -o {os.path.join(self.build_folder, "libbstr.so")}')
        else:
            lib = os.path.join(self.build_folder, "libbstr.a")
            self.run(f'{ar} rcs {lib} {" ".join(objs)}')
            self.run(f'{ranlib} {lib}')

    def package(self):
        copy(self, "libbstr.*", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        for h in self._headers:
            copy(self, h, src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["bstr"]