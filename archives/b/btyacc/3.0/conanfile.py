#!/usr/bin/env python3
"""Conan recipe for btyacc — backtracking yacc parser generator (command-line tool).

Plain Makefile project (no configure script). Build products: the `btyacc`
executable (R38 tool type). The upstream Makefile hardcodes CC=LINKER=gcc;
we override with the Conan toolchain compiler (clang) at build time (R33).
No source patches required.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class BtyaccConan(ConanFile):
    name = "btyacc"
    version = "3.0"
    description = "btyacc — backtracking yacc parser generator (C)"
    license = "Public-Domain"
    homepage = "http://www.siber.com/btyacc/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # In-tree build: btyacc's Makefile uses relative source paths
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler must come from Conan Toolchain conf, not bare ${CC}
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c", "clang")
        # Upstream Makefile hardcodes CC=LINKER=gcc; override with toolchain clang
        self.run(f"make CC={cc} LINKER={cc} -j1", env="conanbuild")

    def package(self):
        # Makefile install target (`cp btyacc.exe /bin`) is not usable;
        # copy the built binary manually (same approach as aescrypt)
        copy(self, "btyacc", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]