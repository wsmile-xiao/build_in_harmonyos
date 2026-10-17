#!/usr/bin/env python3
"""Conan recipe — libco 1.0 (Tencent coroutine library).

Build system: plain Makefile (no configure, no install target).
Upstream `make colib` produces lib/libcolib.a + solib/libcolib.so;
public headers are co_routine.h / coctx.h (no extern "C" — C++ only API).
License: Apache-2.0 (Tencent).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class LibcoConan(ConanFile):
    name = "libco"
    version = "1.0"
    description = "libco - a coroutine library for C/C++ (Tencent)"
    license = "Apache-2.0"
    homepage = "https://github.com/Tencent/libco"
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

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        GnuToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compilers come from Conan conf, never bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"
        # `colib` target builds libcolib.a + libcolib.so only (examples are
        # upstream smoke tests, exercised in notes.md, not packaged).
        self.run(f'make -j1 colib CC="{cc}" CXX="{cxx}"', cwd=self.source_folder)

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        # Package only the artifact matching the selected linkage so
        # consumers get deterministic -lcolib resolution.
        if self.options.shared:
            copy(self, "libcolib.so", src=os.path.join(self.source_folder, "solib"), dst=libdir)
        else:
            copy(self, "libcolib.a", src=os.path.join(self.source_folder, "lib"), dst=libdir)
        copy(self, "*.h", src=self.source_folder, dst=incdir)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["colib"]
