#!/usr/bin/env python3
"""Conan recipe — lxsplit (command-line file splitter/joiner).

lxSplit splits and merges files without compression; it is fully
compatible with HJSplit. It produces a single binary, no libraries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class LxsplitConan(ConanFile):
    name = "lxsplit"
    version = "0.2.4"
    description = "Command-line file splitter/joiner compatible with HJSplit"
    license = "GPL-2.0-or-later"
    homepage = "https://lxsplit.sourceforge.net/"

    # CLI tool, not a library — do not expose cpp_info.libs.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # lxsplit is a pure C program; only depends on libc.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: Get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")

        # The upstream Makefile builds and runs `mkuoff_t` to generate
        # uoff_t.h (it probes sizeof(long)/sizeof(off_t) at compile time).
        # Its header warns this is "NOT suitable for cross-compiling", but
        # on OHOS the build profile matches the host arch (aarch64), so the
        # helper binary runs natively — no patch or cross-run workaround is
        # needed. The Makefile already honours LFS (-D_FILE_OFFSET_BITS=64)
        # and appends -Wall -W -DNO_DEBUG to user CFLAGS.
        # R9: -j1 to avoid parallel build issues.
        self.run(f"make CC={cc} -j1")

    def package(self):
        # lxsplit is a single binary tool — copy to bin/
        copy(self, "lxsplit", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Application package — binary is in bin/
        self.cpp_info.bindirs = ["bin"]
