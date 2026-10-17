#!/usr/bin/env python3
"""Conan recipe for hashmap 0.8.1 — single-file C library (no build system).

hashmap.c ships hashmap.c (implementation, 1154 lines) + hashmap.h (API).
Upstream has no configure/make; the shipped test entry is
`cc -DHASHMAP_TEST hashmap.c && ./a.out`.  This recipe compiles the
single translation unit into a static library (R26: static by default)
and installs the public header.

R33: compiler executable is taken from Conan conf, never from shell env.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HashmapConan(ConanFile):
    name = "hashmap"
    version = "0.8.1"
    description = "An efficient hashmap (hash table) implementation written in C"
    license = "MIT"
    homepage = "https://github.com/tidwall/hashmap.c"
    url = "https://github.com/tidwall/hashmap.c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # hashmap 0.8.1 has no forced third-party dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler/archiver from Conan conf, never bare ${CC}/${AR}.
        # tools.build:compiler_executables is a dict; read it as such.
        execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = execs.get("c", "clang")
        ar = execs.get("ar", "llvm-ar")
        ranlib = execs.get("ranlib", "llvm-ranlib")
        cflags = ""
        if self.settings.compiler == "clang" or self.settings.compiler == "apple-clang":
            cflags = "-O2 -fPIC"
        elif self.settings.compiler == "gcc":
            cflags = "-O2 -fPIC"
        if self.settings.build_type == "Debug":
            cflags = cflags.replace("-O2", "-O0 -g")
        # Single translation unit → static archive (shared builds compile the
        # same source with -fPIC into a .so).
        if self.options.shared:
            libname = os.path.join(self.build_folder, "libhashmap.so")
            self.run(f"{cc} {cflags} -shared -o {libname} {os.path.join(self.source_folder, 'hashmap.c')}")
        else:
            obj = os.path.join(self.build_folder, "hashmap.o")
            lib = os.path.join(self.build_folder, "libhashmap.a")
            self.run(f"{cc} {cflags} -c {os.path.join(self.source_folder, 'hashmap.c')} -o {obj}")
            self.run(f"{ar} rcs {lib} {obj}")
            self.run(f"{ranlib} {lib}")

    def package(self):
        copy(self, "hashmap.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libhashmap.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libhashmap.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["hashmap"]
