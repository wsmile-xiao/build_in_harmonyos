#!/usr/bin/env python3
"""Conan recipe — tinycthread 1.1

TinyCThread — minimalist, portable C11-like threading library
(threads, mutex, condvar, TLS). Library is a single C file
(source/tinycthread.c) plus header; no configure, no library Makefile
(upstream only ships test/ programs' Makefile).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TinycthreadConan(ConanFile):
    name = "tinycthread"
    version = "1.1"
    description = "TinyCThread - a minimalist, portable threading library for C (C11-like subset: threads, mutex, condvar, TLS)"
    license = "MIT"
    homepage = "http://tinycthread.bitsnbites.eu/"
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

    # R32: OHOS/Linux platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        ar = comp_execs.get("ar") or "llvm-ar"
        # tinycthread has no library Makefile (only test/ Makefile): compile the
        # single-file library directly.
        src = os.path.join(self.source_folder, "source", "tinycthread.c")
        self.run(f'"{cc}" -c -std=c99 -O2 -fPIC -I{os.path.join(self.source_folder, "source")} "{src}" -o tinycthread.o',
                 cwd=self.build_folder)
        self.run(f'"{ar}" rcs libtinycthread.a tinycthread.o', cwd=self.build_folder)

    def package(self):
        copy(self, "tinycthread.h", src=os.path.join(self.source_folder, "source"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libtinycthread.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["tinycthread"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
