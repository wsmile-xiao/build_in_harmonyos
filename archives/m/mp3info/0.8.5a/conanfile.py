#!/usr/bin/env python3
"""Conan recipe — mp3info 0.8.5a (MP3 technical info viewer and ID3 tag editor).

mp3info is a command-line tool for viewing MP3 file technical information
(bitrate, sample rate, playtime, etc.) and editing ID3 1.x tags. It also
provides an ncurses-based interactive interface.

The upstream uses a plain Makefile (no configure script). Only the CLI
binary (mp3info) is built; the GTK2 GUI (gmp3info) is skipped because OHOS
has no GTK2.

OHOS CI workers ship the ncurses runtime library but NOT the development
headers (confirmed by the bitwise/nudoku recipes), so the ncurses headers
and a matching static libncursesw.a are bundled under res/ and used directly
(same approach as nudoku and bitwise).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.layout import basic_layout


class Mp3InfoConan(ConanFile):
    name = "mp3info"
    version = "0.8.5a"
    description = "MP3 technical info viewer and ID3 1.x tag editor"
    license = "MIT"
    homepage = "https://www.ibiblio.org/pub/linux/apps/sound/mp3-utils/mp3info/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Bundle ncurses headers + static lib (res/) — CI workers ship the
        # ncurses runtime but lack the dev headers/static archive.
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def requirements(self):
        # R27: ncurses is a system runtime library (no Conan recipe); its
        # headers/lib are bundled because CI workers lack the dev package.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Copy bundled ncurses headers/lib from the export folder into the
        # source folder so build() can reach them.
        export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
        res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")

        src = self.source_folder
        out = self.build_folder

        # Bundled ncurses (CI workers lack dev headers).
        bundled_inc = os.path.join(src, "res", "headers")
        bundled_lib = os.path.join(src, "res", "libs")
        if not os.path.isdir(bundled_inc):
            raise RuntimeError(f"bundled ncurses headers missing: {bundled_inc}")

        # Fix: uint -> unsigned int (musl libc does not define uint)
        replace_in_file(self, os.path.join(src, "mp3tech.c"),
                        "*(uint*)", "*(unsigned int*)")

        # Source files (from Makefile: SRCS = mp3info.c textfunc.c mp3curs.c mp3tech.c)
        cflags = f"-fPIC -O2 -Wall -I{bundled_inc}"
        nc_libs = f"-L{bundled_lib} -lncursesw"

        objs = []
        for srcfile in ["mp3info.c", "textfunc.c", "mp3curs.c", "mp3tech.c"]:
            obj = os.path.join(out, srcfile.replace(".c", ".o"))
            self.run(f"{cc} {cflags} -c {src}/{srcfile} -o {obj}")
            objs.append(obj)

        # Link mp3info binary (skip gmp3info which needs GTK2)
        self.run(f"{cc} {' '.join(objs)} {nc_libs} -o {out}/mp3info")

    def package(self):
        copy(self, "mp3info", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mp3info.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
