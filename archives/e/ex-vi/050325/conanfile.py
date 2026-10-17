#!/usr/bin/env python3
"""Conan recipe for ex-vi 050325 — traditional vi/ex editor (Makefile project).

ex-vi is the traditional BSD vi/ex editor. It is a pure Makefile project
(no ./configure script), with no external dependencies (bundles libterm/
and libuxre/). Build produces executables: ex, exrecover, expreserve
(plus symlinks vi, edit, vedit, view).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ExViConan(ConanFile):
    name = "ex-vi"
    version = "050325"
    description = "Traditional BSD vi/ex line editor (ex-vi 050325)"
    license = "BSD-3-Clause"
    homepage = "https://ex-vi.sourceforge.net/"
    url = ""  # CI fills this

    # This is a command-line tool (executables), not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ex-vi has no external dependencies — it bundles libterm/ (termcap)
        # and libuxre/ (regex) and mapmalloc.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No AutotoolsToolchain needed — this is a raw Makefile project.
        # Compiler and flags are passed directly to make.
        pass

    def _get_cc(self):
        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return comp_execs.get("c", "clang")

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()

        # ex-vi Makefile accepts CC and CFLAGS as make variables.
        # The sub-Makefiles (libterm, libuxre) use 'override CFLAGS' to
        # preserve their internal flags (-I., -D defines) when CFLAGS is
        # passed from the command line.
        cflags = "-fPIC -O2"

        # PREFIX is used at compile time for RECOVER paths (exrecover/expreserve
        # locations). We use the package_folder so the installed binaries find
        # each other at runtime.
        prefix = self.package_folder

        # R9: Use -j1 (HMDFS filesystem doesn't support make jobserver fifos).
        # CRITICAL: CFLAGS value must be shell-quoted — it contains a space
        # ("-fPIC -O2"). Without quotes, self.run() passes it through the
        # shell and "-O2" becomes a separate make argument, which GNU make
        # parses as "-O" (output-sync) with type "2", aborting with
        # "unknown output-sync type '2'". Same applies to PREFIX (contains
        # spaces in paths) and CC (absolute path, no spaces but quoted for
        # consistency with the accrete/agetty recipes).
        self.run(
            f'make -j1 CC="{cc}" CFLAGS="{cflags}" PREFIX="{prefix}"',
            cwd=self.source_folder,
        )

    def package(self):
        # Install using the Makefile's install target.
        # The Makefile installs to $(DESTDIR)$(PREFIX)/bin/ etc.
        # DESTDIR must be EMPTY so files go directly into package_folder
        # (PREFIX). If DESTDIR == PREFIX (a prior bug), the path doubles
        # to package_folder/package_folder/bin/ and the test_package
        # cannot find the binary on PATH.
        prefix = self.package_folder

        # PRESERVEDIR: install recovery files under PREFIX/var/preserve
        # to avoid needing /var/preserve (which may not be writable).
        preservedir = os.path.join(prefix, "var", "preserve")

        # Shell-quote PREFIX/PRESERVEDIR (paths may contain spaces).
        # DESTDIR is intentionally empty — see comment above.
        self.run(
            f'make install PREFIX="{prefix}" '
            f'PRESERVEDIR="{preservedir}" DESTDIR=',
            cwd=self.source_folder,
        )

    def package_info(self):
        # This is an application (command-line tool), not a library.
        # cpp_info.libs is empty — the build produces executables in bin/.
        self.cpp_info.libs = []
        # bindirs is set by default to ["bin"] which is correct for this tool.
        # The executables are: ex (with symlinks vi, edit, vedit, view),
        # exrecover, expreserve (in libexec).
