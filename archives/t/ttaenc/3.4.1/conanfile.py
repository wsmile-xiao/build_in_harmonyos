#!/usr/bin/env python3
"""Conan recipe for ttaenc 3.4.1 — TTA (True Audio) lossless audio encoder/decoder.

ttaenc is a command-line tool for compressing/decompressing lossless audio
using the TTA format. It is a simple C project built with a Makefile.

Platform adaptations for OHOS:
  1. Makefile: Use $(CC) instead of gcc; add DESTDIR/PREFIX support; remove strip
  2. ttaenc.h: Replace __uint32_t/__uint64_t with stdint.h types
  3. ttaenc.c: Replace __inline with static inline (C99 compliance)

R28: test_package/ exists.
R32: settings.os supports OHOS.
R38: commands.json declared (command-line tool).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TtaencConan(ConanFile):
    name = "ttaenc"
    version = "3.4.1"
    description = "TTA (True Audio) lossless audio encoder/decoder"
    license = "GPL-2.0"
    homepage = "https://tausoft.org/"
    url = ""  # CI fills this

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

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # R9: Always use -j1
        self.run(f"make -C {self.source_folder} CC={cc} CFLAGS='-Wall -O3 -fPIC' -j1")

    def package(self):
        # Copy the ttaenc binary to bin/
        copy(self, "ttaenc", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool: no libraries, just executable in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
