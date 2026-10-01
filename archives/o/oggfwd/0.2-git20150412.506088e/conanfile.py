#!/usr/bin/env python3
"""Conan recipe — oggfwd 0.2-git20150412.506088e (plain Makefile).

oggfwd is a tiny Icecast source client: it reads an Ogg stream from stdin and
forwards it to an Icecast server through libshout.

Upstream: J^ / rafael2k / Philipp Schafft (GPL-2.0), Debian orig snapshot of
git commit 506088e (2015-04-12).

Adaptation notes (see notes.md):
  * The upstream Makefile has no configure step; it honours CC / CFLAGS /
    INCLUDEFLAGS / LINKFLAGS from the environment or the command line, so no
    source patch is needed.
  * `make install` uses `install -o root -g bin`, which fails for non-root
    builders and on musl (no `bin` group) -> package() installs the binary and
    man page explicitly.
  * libshout/2.4.6 is a static library whose codec / TLS dependencies must be
    on the link line: the full -I/-L/-l set is taken from the Conan dependency
    graph via AutotoolsDeps (no shell variables, R33).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OggfwdConan(ConanFile):
    name = "oggfwd"
    version = "0.2-git20150412.506088e"
    description = "Icecast source client: forwards an Ogg stream from stdin to an Icecast server via libshout"
    license = "GPL-2.0-only"
    homepage = "https://icecast.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/o/oggfwd/0.2-git20150412.506088e"

    package_type = "application"
    languages = "C"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libshout/2.4.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
        deps = AutotoolsDeps(self).vars()
        cppflags = deps.get("CPPFLAGS", "")
        ldflags = deps.get("LDFLAGS", "")
        libs = deps.get("LIBS", "")
        autotools = Autotools(self)
        autotools.make(
            target="oggfwd",
            args=[
                "-j1",
                "-C",
                f'"{self.source_folder}"',
                f"CC={cc}",
                f'"INCLUDEFLAGS={cppflags}"',
                f'"LINKFLAGS={ldflags} -Wl,--as-needed {libs}"',
            ],
        )

    def package(self):
        copy(self, "oggfwd", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "oggfwd.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
