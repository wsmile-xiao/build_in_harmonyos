#!/usr/bin/env python3
"""Conan recipe for lr 2.0.1 — a better recursive ls/find (single-file C tool).

lr is a single-file C program (lr.c, ~1500 lines) built with a raw POSIX
Makefile (no configure script, no test target).  It produces an
*executable* (not a library), so:
  - package_type = "application"
  - No shared/static options; zero external dependencies (libc only)
  - package_info() sets bindirs (no libs)

OHOS notes
----------
* The `#ifdef __linux__` code path in lr.c (getmntent/mntent for mount
  table support) applies on OHOS (Linux kernel defines __linux__), and
  lr.c compiles cleanly with the OHOS clang — no patches needed.
* The Makefile `install` target requires the coreutils `install`
  command, which the OHOS platform lacks (E098/E108); packaging uses
  Conan copy() directly instead (endlessh precedent).
* source(): the codeload URL ends in the tag name `v2.0.1` (no file
  extension), so an explicit *.tar.gz filename is passed to get() to
  keep Conan's unzip() on the tar.gz decoder (endlessh precedent).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LrConan(ConanFile):
    name = "lr"
    version = "2.0.1"
    description = "lr - a better recursive ls/find: lists files recursively with embedded filter expressions"
    license = "MIT"
    homepage = "https://github.com/leahneukirchen/lr"
    url = ""  # CI fills this

    # This is an executable, NOT a library
    package_type = "application"

    # CI L0p requires all four settings (os, compiler, build_type, arch).
    settings = "os", "compiler", "build_type", "arch"

    # No options — executables don't need shared/static
    # No dependencies — lr is self-contained (libc only)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URLs end in the tag name (e.g. ".../tar.gz/refs/tags/v2.0.1")
        # which has no file extension, so Conan's get() deduces filename
        # "v2.0.1" and unzip() falls back to the zip decoder → BadZipFile.
        # Pass an explicit *.tar.gz filename so unzip() selects the tar.gz
        # decoder.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="lr-2.0.1.tar.gz")

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from ${CC} shell env var.
        # The profile sets tools.build:compiler_executables as a dict
        # {'c': '/data/service/hnp/bin/clang', ...}, so fetch the whole dict.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # R9: Always -j1 (single-file program, -j1 is sufficient and required).
        self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        # The OHOS platform lacks the `install` coreutils command, so we use
        # Conan's copy() directly instead of `make install DESTDIR=...`.
        copy(self, "lr", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "lr.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "_lr", self.source_folder, os.path.join(self.package_folder, "share", "zsh", "site-functions"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # For application packages: declare bindirs so consumers can find the
        # executable on PATH.  No libs (this is not a library).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
