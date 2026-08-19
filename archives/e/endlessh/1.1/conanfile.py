#!/usr/bin/env python3
"""Conan recipe for endlessh 1.1 — SSH tarpit (single-file C program).

endlessh is a single-file C program built with a raw POSIX Makefile (no
configure script).  It produces an *executable* (not a library), so:
  - package_type = "application"
  - No shared/static options
  - No external dependencies
  - package_info() sets bindirs (no libs)

Build: make CC=clang -j1   (R9: -j1; R33: use Conan conf, not ${CC} env var)
Install: the OHOS platform has no `install` coreutils command, so we use
         Conan copy() instead of `make install DESTDIR=...`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EndlesshConan(ConanFile):
    name = "endlessh"
    version = "1.1"
    description = "SSH tarpit that slowly sends an endless banner to keep SSH clients stuck"
    license = "Unlicense"
    homepage = "https://github.com/skeeto/endlessh"
    url = ""  # CI fills this

    # This is an executable, NOT a library
    package_type = "application"

    # CI L0p requires all four settings (os, compiler, build_type, arch).
    settings = "os", "compiler", "build_type", "arch"

    # No options — executables don't need shared/static
    # No dependencies — endlessh is self-contained

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # endlessh has zero external dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URLs end in the tag name (e.g. ".../tar.gz/refs/tags/1.1")
        # which has no file extension, so Conan's get() deduces filename "1.1"
        # and unzip() falls back to the zip decoder → BadZipFile.  Pass an
        # explicit *.tar.gz filename so unzip() selects the tar.gz decoder.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="endlessh-1.1.tar.gz")

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
        copy(self, "endlessh", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "endlessh.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # For application packages: declare bindirs so consumers can find the
        # executable on PATH.  No libs (this is not a library).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
