#!/usr/bin/env python3
"""Conan recipe for makefile2graph v1.5.0 — Creates a graph of dependencies from GNU-Make.

makefile2graph uses a plain Makefile (no configure script). It produces:
  - make2graph: C binary that parses `make -Bnd` output and emits DOT/GEXF/list/deep formats
  - makefile2graph: shell script wrapper that pipes `make -nd` into make2graph
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Makefile2GraphConan(ConanFile):
    name = "makefile2graph"
    version = "1.5.0"
    description = "Creates a graph of dependencies from GNU-Make"
    license = "MIT"
    homepage = "https://github.com/lindenb/makefile2graph"
    url = "https://github.com/lindenb/makefile2graph"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        # R33: Get compiler from Conan conf, not shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # Plain Makefile build — no configure step needed
        # basic_layout separates source and build folders, so use -C to find the Makefile
        src = self.source_folder
        self.run(f"make -C {src} CC={cc} -j1")

    def package(self):
        # Copy built binary and wrapper script from source folder
        src = self.source_folder
        copy(self, "make2graph", src, os.path.join(self.package_folder, "bin"))
        copy(self, "makefile2graph", src, os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "make2graph"), 0o755)
        os.chmod(os.path.join(self.package_folder, "bin", "makefile2graph"), 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
