#!/usr/bin/env python3
"""Conan recipe — memtester 4.7.1 (userspace memory tester).

Upstream ships a djb-style Makefile that drives the build through generated
shell scripts (warn-auto.sh / compile / load) carrying ``#!/bin/sh`` shebangs.
OHOS has no ``/bin/sh`` (R5), so those scripts cannot execute. Instead of
calling ``make``, this recipe compiles the two C sources directly with the
upstream-equivalent flags (read from conf-cc / conf-ld). The produced binary
is identical in behaviour to an upstream ``make`` build.

memtester links only against libc (mmap/mlock/malloc); it has no library API
and no external dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MemtesterConan(ConanFile):
    name = "memtester"
    version = "4.7.1"
    description = "Userspace utility for testing the memory subsystem for faults"
    license = "GPL-2.0-only"
    homepage = "https://pyropus.ca/software/memtester/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: read the compiler from Conan conf, never from undefined shell vars.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._get_cc()
        # Flags mirrored verbatim from upstream conf-cc / conf-ld.
        cflags = (
            "-O2 -DPOSIX -D_POSIX_C_SOURCE=200809L "
            "-D_FILE_OFFSET_BITS=64 -DTEST_NARROW_WRITES"
        )
        src = self.source_folder
        # memtester links only against libc; no extra libraries or includes.
        self.run(f'"{cc}" {cflags} -c "{src}/memtester.c" -o "{src}/memtester.o"', cwd=src)
        self.run(f'"{cc}" {cflags} -c "{src}/tests.c" -o "{src}/tests.o"', cwd=src)
        self.run(f'"{cc}" -s -o "{src}/memtester" "{src}/memtester.o" "{src}/tests.o"', cwd=src)

    def package(self):
        # HarmonyOS lacks a reliable `make install`; copy the artefacts directly.
        copy(self, "memtester", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "memtester.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        binary = os.path.join(self.package_folder, "bin", "memtester")
        if os.path.exists(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
