#!/usr/bin/env python3
"""Conan recipe — exceptions4c 3.0.5 (C library, src/e4c.c + src/e4c.h).

exceptions4c is a tiny, portable C exception-handling library. The upstream
"build" is simply dropping src/e4c.c + src/e4c.h into the consumer project
(see README: "you have to drop the two files in your project"). There is no
top-level make/configure for the library itself; test/ contains the upstream
test harness with its own Makefile.

Adaptation approach:
  - compile src/e4c.c -> libexceptions4c.a (static, R26-safe: no system name clash)
  - install src/e4c.h as public header
  - upstream tests (test/ dir) are enumerated/run separately in notes/tests.

Key rules applied:
  - R33: compiler flags from Conan conf, never bare ${CC}/${CFLAGS}
  - R9:  -j1 builds
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Exceptions4CConan(ConanFile):
    name = "exceptions4c"
    version = "3.0.5"
    description = "Exceptions for C: a tiny, portable exception handling library for C"
    license = "MIT"
    homepage = "https://github.com/guillermocalvo/exceptions4c"
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

        # R33: compiler from Conan conf, never from shell env
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        ar = comp_execs.get("ar") or "llvm-ar"
        ranlib = comp_execs.get("ranlib") or "llvm-ranlib"

        # Library source lives in src/e4c.c (header src/e4c.h)
        src_dir = os.path.join(self.source_folder, "src")
        # R9; static archive only (shared=False default; no PIC-needed consumers)
        self.run(f"{cc} -fPIC -O2 -I{src_dir} -c {src_dir}/e4c.c -o e4c.o", cwd=self.build_folder)
        self.run(f"{ar} rcs libexceptions4c.a e4c.o", cwd=self.build_folder)
        self.run(f"{ranlib} libexceptions4c.a", cwd=self.build_folder)

    def package(self):
        copy(self, "e4c.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "libexceptions4c.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["exceptions4c"]
        # e4c.h must be included with its directory name (#include "e4c.h" works
        # when including from consumer; keep default include path)
        self.cpp_info.includedirs = ["include"]