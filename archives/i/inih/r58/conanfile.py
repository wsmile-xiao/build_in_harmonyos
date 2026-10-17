#!/usr/bin/env python3
"""Conan recipe for inih r58 — direct compilation.

inih (INI Not Invented Here) is a simple INI file parser written in C.
Only two source files (ini.c + ini.h), no external dependencies.
Compiled directly with clang into a static library — no Meson needed.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, mkdir
from conan.tools.layout import basic_layout


class InihConan(ConanFile):
    name = "inih"
    version = "r58"
    description = "Simple INI file parser in C, good for embedded systems"
    license = "BSD-3-Clause"
    homepage = "https://github.com/benhoyt/inih"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # inih has zero external dependencies — pure C standard library
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        """Collect compiler and archiver paths from profile."""
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        self._cc_c = ce.get("c", "clang")
        # Infer ar from compiler bin dir if not explicitly provided
        ar = ce.get("ar") or ""
        if not ar:
            cc_path = (ce.get("c") or "").strip()
            if cc_path:
                bindir = os.path.dirname(cc_path)
                for cand in ("llvm-ar", "ar"):
                    full = os.path.join(bindir, cand)
                    if os.path.isfile(full):
                        ar = full
                        break
        self._ar = ar or "ar"

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc_c
        ar = self._ar
        cflags = ""
        if self.settings.build_type == "Debug":
            cflags += " -g -O0"
        else:
            cflags += " -O2"
        src_dir = self.source_folder
        build_dir = self.build_folder
        self.run(f"{cc} -c {cflags} -o \"{build_dir}/ini.o\" \"{src_dir}/ini.c\"")
        self.run(f"{ar} rcs \"{build_dir}/libinih.a\" \"{build_dir}/ini.o\"")

    def package(self):
        mkdir(self, os.path.join(self.package_folder, "lib"))
        mkdir(self, os.path.join(self.package_folder, "include"))
        copy(self, "ini.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libinih.a", self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["inih"]
        self.cpp_info.set_property("cmake_file_name", "inih")
        self.cpp_info.set_property("cmake_target_name", "inih::inih")
