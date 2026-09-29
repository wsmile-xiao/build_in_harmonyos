#!/usr/bin/env python3
"""Conan recipe — libpqueue 09b72d55c4 (no build system, plain C).

libpqueue is a generic priority queue (binary heap) implementation used by
the Apache HTTP Server project. The upstream tarball contains only
src/pqueue.c + src/pqueue.h + sample programs — there is no configure
script, Makefile or CMakeLists. We compile the single C source into a
static library directly.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibpqueueConan(ConanFile):
    name = "libpqueue"
    version = "09b72d55c4"
    description = "A generic priority queue (heap) implementation in C"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vy/libpqueue"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = (comp.get("c", "clang") if comp else "clang") or "clang"
        ar = (comp.get("lib", "llvm-ar") if comp else "llvm-ar") or "llvm-ar"

        src = self.source_folder
        build_folder = self.build_folder

        # Compile the single C source into a static library.
        self.run(
            f"{cc} -Wall -O2 -fPIC -I{src}/src -c {src}/src/pqueue.c -o {build_folder}/pqueue.o",
            env="conanbuild",
        )
        self.run(
            f"{ar} rcs {build_folder}/libpqueue.a {build_folder}/pqueue.o",
            env="conanbuild",
        )
        if self.options.shared:
            # Being a single .c library, shared is built via cc -shared on the .o.
            self.run(
                f"{cc} -shared -fPIC -o {build_folder}/libpqueue.so {build_folder}/pqueue.o",
                env="conanbuild",
            )

    def package(self):
        build_folder = self.build_folder
        libext = ".so" if self.options.shared else ".a"
        copy(self, f"libpqueue{libext}", src=build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "pqueue.h", src=os.path.join(self.source_folder, "src"), dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["pqueue"]