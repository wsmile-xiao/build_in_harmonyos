#!/usr/bin/env python3
"""Conan recipe for odo 0.2.2 -- atomic odometer for the command line.

odo is an atomic, concurrency-safe odometer: it keeps a counter in a
memory-mapped file and updates it with compare-and-swap, so that many
processes can increment/read/set a shared counter concurrently.

Build: plain Makefile (C99 + POSIX), no configure, no third-party deps.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OdoConan(ConanFile):
    name = "odo"
    version = "0.2.2"
    description = "An atomic odometer for the command line"
    license = "ISC"
    homepage = "https://github.com/atomicobject/odo"
    url = "https://github.com/atomicobject/odo"  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from the Conan toolchain conf, never a bare shell var.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "odo", src, bin_dir, keep_path=False)
        copy(self, "odo.1", os.path.join(src, "man"), man_dir, keep_path=False)
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"),
             "Copyright (c) 2014 Scott Vokes <scott.vokes@atomicobject.com>\n"
             "Permission to use, copy, modify, and/or distribute this software "
             "for any purpose with or without fee is hereby granted.\n")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
