#!/usr/bin/env python3
"""Conan recipe for wiggle 1.3 — raw Makefile build system.

wiggle applies patches to files that are not identical to the ones the patches
were generated from (extract/merge/reverse). Upstream builds `./wiggle` with a
plain Makefile against ncurses and registers its regression suite through the
`dotest` script (71 cases under `tests/`, wired to the `test` make target).

Build notes:
- The default `all` target also renders `wiggle.man` via `nroff`, which is not
  part of the toolchain; the recipe builds the `wiggle` target only and the
  package step installs the preexisting `wiggle.1` roff source as documentation.
- `CWFLAGS` is overridden on the command line: upstream defaults carry
  `-Werror` (unsafe with a different clang) and no dependency include path.
- Upstream links `-lncurses`; the ohpcd ncurses package ships the wide-character
  static library, so `LDLIBS` links `-lncursesw` from the dependency's lib dir.
- The upstream regression suite (`./dotest`, 71 cases) runs inside build(); on
  this platform it executes natively and passes 71/71.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class WiggleConan(ConanFile):
    name = "wiggle"
    version = "1.3"
    description = "Apply patches that 'patch' rejects: extract, merge and reverse fuzzy patches"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/neilbrown/wiggle"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)
        # wiggle builds in-source (Makefile writes ./wiggle next to the sources)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get the compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R5: OHOS has no /bin/sh guarantees; use CONFIG_SHELL from profile [buildenv].
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        dep = self.dependencies["ncurses"]
        incdir = dep.cpp_info.includedirs[0]
        if not os.path.isabs(incdir):
            incdir = os.path.join(dep.package_folder, incdir)
        libdir = dep.cpp_info.libdirs[0]
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)

        # Command-line overrides (make command-line variables beat makefile
        # assignments): keep upstream warnings minus -Werror, add the ncursesw
        # include dir, link the wide-character static library.
        cwflags = (" -Wall -Wstrict-prototypes -Wextra"
                   " -Wno-unused-parameter -Wno-missing-field-initializers"
                   f" -I{incdir}")
        self.run(
            f"make wiggle OptDbg=-O2 CWFLAGS='{cwflags}'"
            f" LDLIBS='-L{libdir} -lncursesw' CC={cc} SHELL={config_shell} -j1",
            cwd=self.source_folder,
        )

        # Upstream regression suite: 71 registered cases under tests/ (the
        # `test` make target without the nroff-dependent `all` prerequisites).
        self.run("./dotest", cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "wiggle", src=self.source_folder, dst=bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "wiggle"), 0o755)
        copy(self, "wiggle.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
