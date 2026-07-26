#!/usr/bin/env python3
"""Conan recipe — crunch 3.6 (wordlist generator, Makefile).

crunch is a wordlist generator for brute-force password cracking. It is a
single-file C99 program linking against libm and pthread. OHOS provides both
libraries, so no platform patches are needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CrunchConan(ConanFile):
    name = "crunch"
    version = "3.6"
    description = "Wordlist generator for brute-force password cracking"
    license = "GPL-2.0-only"
    homepage = "https://github.com/crunchsec/crunch"
    url = ""  # CI fills this

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
        # R33: get compiler from Conan conf, never from shell env vars.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"
        src = self.source_folder
        flags = "-Wall -pedantic -std=c99 -pthread"
        # Match upstream Makefile: $(CC) $(CPPFLAGS) $(CFLAGS_STD) $(CFLAGS) $(LFS) $? $(LIBFLAGS) $(LDFLAGS) -o $@
        self.run(f'"{cc}" {flags} "{src}/crunch.c" -lm -o "{src}/crunch"', cwd=src)

    def package(self):
        copy(self, "crunch", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "crunch.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "charset.lst", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "crunch"))
        binary = os.path.join(self.package_folder, "bin", "crunch")
        if os.path.exists(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]