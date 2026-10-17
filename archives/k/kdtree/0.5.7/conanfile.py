#!/usr/bin/env python3
"""Conan recipe for kdtree 0.5.7 — simple ANSI C kd-tree library.

Build: handwritten `./configure` (generates Makefile from Makefile.in),
then `make` builds libkdtree.a and libkdtree.so.0.1.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class KdtreeConan(ConanFile):
    name = "kdtree"
    version = "0.5.7"
    description = "A simple, easy to use C library for working with kd-trees"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jtsiomb/kdtree"
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

        # R33: never rely on ${CC}/${CFLAGS} shell vars — get compilers from
        # Conan conf (tools.build:compiler_executables), never from shell env.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = comp_execs.get("c") or "clang"
        ar = comp_execs.get("ar") or "llvm-ar"
        ranlib = comp_execs.get("ranlib") or "llvm-ranlib"

        # The handwritten configure only honors --prefix and silently ignores
        # unknown options, so a plain shell is sufficient (no autotools).
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        prefix = self.package_folder
        src = self.source_folder
        self.run(f"{config_shell} ./configure --prefix={prefix} --disable-debug", cwd=src)
        if not self.options.shared:
            # Static-only build: keep the static archive and skip the shared lib.
            self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1 libkdtree.a", cwd=src)
        else:
            self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1", cwd=src)

    def package(self):
        copy(self, "kdtree.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "*.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "*.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
            # follow the soname symlinks into the package
            copy(self, "libkdtree.so*", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["kdtree"]
