#!/usr/bin/env python3
"""Conan recipe for socket — create TCP sockets from the shell.

socket(1) connects a TCP socket to stdin/stdout (client mode) or listens on
a port and hands the connection to stdio or to a program (`-p`), which makes
it a minimal netcat-style tool.

Key adaptation points for HarmonyOS PC (aarch64):
  - Upstream is from 1992 and uses the BSD `sigvec()` API. The OHOS libc
    defines SIG_SETMASK (POSIX) but ships no `struct sigvec`, so the BSD
    branch was selected and failed to compile; patched to POSIX sigaction
    (patches/0003-utils.c.patch).
  - `globals.h` declared `extern int errno`, which resolves to no symbol on
    a libc where errno is a per-thread macro; replaced by <errno.h>
    (patches/0002-globals.h.patch).
  - The Makefile hard-codes `CC = cc` and overwrites CFLAGS/LDFLAGS, and the
    shapeTools `+all` wrapper re-exports those values to the sub-make as
    command line variables, so externally injected flags were dropped;
    patched to honour external CC/CFLAGS/LDFLAGS (patches/0001-Makefile.patch).
  - CC comes from Conan conf (R33: never rely on bare shell env vars).
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SocketConan(ConanFile):
    name = "socket"
    version = "1.1"
    description = "socket — create TCP sockets from the shell, as client or as server"
    license = "GPL-1.0-or-later"
    homepage = "https://tracker.debian.org/pkg/socket"
    url = "https://ftp.debian.org/debian/pool/main/s/socket"
    topics = ("network", "tcp", "socket", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # AutotoolsToolchain is used only for its environment (CC/CFLAGS/
        # CPPFLAGS/LDFLAGS): the project is a plain Makefile, there is no
        # configure script.
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler comes from Conan conf, never from a bare shell variable.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # `targets` builds the program directly; the default `all` target goes
        # through the shapeTools `+all` recursion, which is not needed here.
        self.run(f'make targets CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        copy(self, "COPYRIGHT", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "socket", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "socket.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
