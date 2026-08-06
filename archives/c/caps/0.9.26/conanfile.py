#!/usr/bin/env python3
"""Conan recipe for caps 0.9.26 — LADSPA audio effects plugin library.

caps is a LADSPA (Linux Audio Developers Simple Plugin API) plugin library.
It uses a custom configure.py + Makefile build system (not autotools/cmake).
The build produces caps.so (LADSPA plugin) and caps.rdf (RDF metadata).

Patches use unconditional POSIX/standard-C adaptations (no #ifdef __OHOS__):
  - Makefile: CC=g++ -> clang++ (g++ unavailable on OHOS)
  - basics.h: <stdint.h> include + standard C99 types (replaces glibc internals)
  - v4f.h / v4f_IIR2.h: standard math functions (replaces GCC builtins)
  - v4f_IIR2.h: portable exp10f via powf fallback
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, rename
from conan.tools.layout import basic_layout


class CapsConan(ConanFile):
    name = "caps"
    version = "0.9.26"
    description = "LADSPA audio effects plugin library"
    license = "GPL-3.0"
    homepage = "https://quitte.de/dsp/caps.html"

    package_type = "shared-library"
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
        # R33: Get C++ compiler from Conan conf (caps Makefile uses CC for C++ compilation)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++")
        # Run configure.py to generate defines.make (SSE detection naturally fails on aarch64)
        self.run("python3 configure.py", cwd=self.source_folder)
        # Build the LADSPA plugin shared library
        self.run(f"make CC={cxx} CXX={cxx} -j1", cwd=self.source_folder)

    def package(self):
        # Copy caps.so and rename to libcaps.so for standard CMake find_library convention
        copy(self, "caps.so", self.source_folder, os.path.join(self.package_folder, "lib"))
        rename(self, os.path.join(self.package_folder, "lib", "caps.so"),
               os.path.join(self.package_folder, "lib", "libcaps.so"))
        # Copy LADSPA RDF metadata
        copy(self, "caps.rdf", self.source_folder, os.path.join(self.package_folder, "share", "ladspa", "rdf"))

    def package_info(self):
        self.cpp_info.libs = ["caps"]
        # caps is a LADSPA plugin (no public headers)
        self.cpp_info.includedirs = []
