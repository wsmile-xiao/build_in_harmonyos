#!/usr/bin/env python3
"""Conan recipe for math-sll 1.24 — fixed-point (32.32) math library.

Upstream build system: raw Makefile (make all / make install), no configure.
R26: library name is not a system-name collision, static by default is fine.
R33: compiler flags come from Conan conf, never shell env vars.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MathsllConan(ConanFile):
    name = "math-sll"
    version = "1.24"
    description = "A fixed point (32.32 bit) math library for C/C++ projects"
    license = "MIT"
    homepage = "https://github.com/aemileski/math-sll"
    url = "https://github.com/aemileski/math-sll"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # math-sll is dependency-free; only libc/libm-style builtins are used.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: obtain compilers from Conan conf, never bare ${CC}/${CFLAGS}
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} STRIP=true -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "math-sll.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # Upstream emits `math-sll.a` (no lib prefix); CMakeDeps looks for the
        # conventional libmath-sll.a name, so rename after copying.
        copy(self, "math-sll.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        os.rename(os.path.join(self.package_folder, "lib", "math-sll.a"),
                  os.path.join(self.package_folder, "lib", "libmath-sll.a"))

    def package_info(self):
        self.cpp_info.libs = ["math-sll"]
