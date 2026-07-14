#!/usr/bin/env python3
"""Conan recipe — nudoku 5.0.4 (ncurses sudoku game).

nudoku is an ncurses-based sudoku (TUI) game. Upstream uses autotools, but the
official GitHub source tarball is a git snapshot shipping only configure.ac
(no pre-generated configure/Makefile.in), so autotools would require autoreconf
+ autopoint(gettext) + pkg-config. The project is just two translation units —
src/main.c (ncurses UI) and src/sudoku.c (pure-C solver) — so we compile them
directly with the Conan-provided clang and expose the solver as libnudoku.a.

OHOS CI workers ship the ncurses runtime library but NOT the development
headers (confirmed by the bitwise recipe), so the ncurses headers and a
matching static libncurses.a are bundled under res/ and used directly (same
approach as bitwise).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file
from conan.tools.layout import basic_layout


class NudokuConan(ConanFile):
    name = "nudoku"
    version = "5.0.4"
    description = "nudoku - ncurses based sudoku game"
    license = "GPL-3.0"
    homepage = "https://github.com/jubalh/nudoku"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
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
        # R33: compiler from Conan conf. The CI profile exposes
        # tools.build:compiler_executables as a dict {'c':..., 'cpp':...}; the
        # ':c' sub-conf is not registered and raises ConanException. ar/ranlib
        # are absent -> derive llvm-ar from the compiler bindir (fontconfig).
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")
        ar = ce.get("ar")
        if not ar:
            _bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            _cand = os.path.join(_bindir, "llvm-ar") if _bindir else ""
            if _cand and os.path.isfile(_cand):
                ar = _cand
        if not ar:
            ar = os.environ.get("AR", "llvm-ar")

        src = self.source_folder
        out = self.build_folder

        # Bundled ncurses (CI workers lack dev headers). The bundled wide-char
        # header is curses.h (== ncurses.h); adapt main.c's #include.
        bundled_inc = os.path.join(src, "res", "headers")
        bundled_lib = os.path.join(src, "res", "libs")
        if not os.path.isdir(bundled_inc):
            raise RuntimeError(f"bundled ncurses headers missing: {bundled_inc}")
        replace_in_file(self, os.path.join(src, "src", "main.c"),
                        "<ncurses.h>", "<curses.h>")

        # VERSION is normally injected by autotools; the \\" lets the shell pass
        # -DVERSION="5.0.4" so VERSION is a string literal in C.
        cflags = (
            "-O2 "
            '-DVERSION=\\"5.0.4\\" '
            '-DLOCALEDIR=\\"/usr/local/share/locale\\" '
            f"-I{bundled_inc}"
        )
        nc_libs = f"-L{bundled_lib} -lncurses"

        # 1) Solver static library (pure C, no ncurses dependency).
        self.run(f"{cc} {cflags} -c {src}/src/sudoku.c -o {out}/sudoku.o")
        self.run(f"{ar} rcs {out}/libnudoku.a {out}/sudoku.o")
        # 2) TUI binary: main.c + libnudoku + bundled ncurses.
        self.run(f"{cc} {cflags} -c {src}/src/main.c -o {out}/main.o")
        self.run(
            f"{cc} {out}/main.o -L{out} -lnudoku {nc_libs} -o {out}/nudoku"
        )

    def package(self):
        copy(self, "nudoku", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Expose the solver so consumers / test_package can call the API.
        copy(self, "libnudoku.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "sudoku.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["nudoku"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
