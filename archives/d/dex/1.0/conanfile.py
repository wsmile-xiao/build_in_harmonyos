#!/usr/bin/env python3
"""Conan recipe — dex 1.0 (plain Makefile, no configure).

dex is a small text editor with ctags support.
Dependencies: libc, ncurses (system pre-installed static library).
R26: Static linking for terminal tools.
R27: No Conan dependencies (ncurses is system-level).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class DexConan(ConanFile):
    name = "dex"
    version = "1.0"
    description = "Dextrous text editor - small and easy to use with ctags support"
    license = "MIT"
    homepage = "https://github.com/tihirvon/dex"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses is a system-level pre-installed dependency (static lib)
        # No Conan  dependency needed
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked
        env = Environment()
        env.define("BUILD_SHARED_LIBS", "OFF")
        # System ncurses paths (headers and static library)
        env.define("CPATH", "/storage/Users/currentUser/usr/local/include")
        env.define("LIBRARY_PATH", "/storage/Users/currentUser/usr/local/lib")
        env.vars(self).save_script("dex_build_env")

    def build(self):
        apply_conandata_patches(self)
        # Plain Makefile project — no configure script
        # R26: ncurses is already a static library (.a), so linking is static
        self.run("make CC=clang HOST_CC=clang prefix=/usr/local -j1",
                 cwd=self.source_folder)

    def package(self):
        # Install to package_folder via DESTDIR with prefix=/ so that
        # bin/ lands at package root (required by G4 artifact check)
        self.run("make install CC=clang HOST_CC=clang prefix=/ DESTDIR={}".format(
            self.package_folder), cwd=self.source_folder)

    def package_info(self):
        # dex is a terminal tool (executable), not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
