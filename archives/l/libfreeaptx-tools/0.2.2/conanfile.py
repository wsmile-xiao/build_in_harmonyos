#!/usr/bin/env python3
"""Conan recipe - libfreeaptx-tools 0.2.2 (freeaptxenc + freeaptxdec).

Upstream: https://github.com/regularhunter/libfreeaptx (tag 0.2.2)

This package ships only the two upstream command line utilities.  The aptX
codec library itself, its public header and libfreeaptx.pc belong to the
separate libfreeaptx package.

libfreeaptx is a hand written POSIX Makefile project (no configure, no CMake),
and its build rules link both tools against the shared library:

    $(UTILITIES): $(LIBNAME)
    .o:
        $(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LIBNAME)

so each tool ends up with a DT_NEEDED entry for libfreeaptx.so.0 and no
RUNPATH at all.  A tools-only package deletes lib/ (the library one owns it),
and the binaries then die during load with

    ./freeaptxenc: error while loading shared libraries: libfreeaptx.so.0:
    cannot open shared object file: No such file or directory

i.e. exit 127 before they can even answer --version.  Upstream does declare
`STATIC_UTILITIES = $(NAME)enc.static $(NAME)dec.static` next to
`.SUFFIXES: .o .c .static`, but ships no matching .c.static rule, so
`make freeaptxenc.static` only answers "No rule to make target" - the static
variant simply cannot be built with the released Makefile.

Patch 0001 therefore relinks each utility from its own object file *plus*
freeaptx.c directly (self-contained binaries, nothing to locate at run time)
and trims default/install down to bin/ so the .so, the header and the
pkg-config file are never built or installed here.

Patch 0002 adds the -V/--version and --help exit status contract: upstream
only knows -h/--help (usage on stderr, `return 1`), `-h` is also `return 1`
and every unknown option falls into the same `return 1` default branch, so the
platform L2 smoke test can never see a 0 exit status.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.layout import basic_layout


class LibfreeaptxToolsConan(ConanFile):
    name = "libfreeaptx-tools"
    version = "0.2.2"
    description = ("aptX / aptX HD codec command line tools - freeaptxenc "
                   "and freeaptxdec, raw 24 bit stereo PCM through stdio")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/regularhunter/libfreeaptx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Distribution package that only carries executables (R38: the
    # commands.json entry lives at the software level).
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must be checked against ("Linux", "OHOS").
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfreeaptx-tools supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        # The Makefile builds in place and has no VPATH support.
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _compilers(self):
        # R33: a raw Makefile project cannot get the compiler injected by a
        # toolchain, and $CC/$CFLAGS of the shell are empty on the CI workers,
        # so the paths have to come from the Conan conf.
        return self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}

    def generate(self):
        # R33: a raw Makefile project takes its compiler from the Conan conf
        # (see build()), so the one thing left for this generator is the
        # profile [buildenv] - PATH with the SDK toolchain and the
        # LD_LIBRARY_PATH that the SDK lld needs.
        # Do NOT save a custom "conanbuild" script here: that would overwrite
        # the aggregated conanbuild environment Conan builds from every
        # generator and the following self.run() breaks (the same finding is
        # recorded in the mydumper recipe).
        VirtualBuildEnv(self).generate()

    def build(self):
        cc = self._compilers().get("c", "clang")
        # The upstream Makefile assigns `CFLAGS = -W -Wall -O3` unconditionally,
        # which beats an environment CFLAGS, so the flags are handed over as a
        # command line variable (the highest make priority).
        # -fPIC is required now that freeaptx.c is compiled straight into the
        # executables: with a PIE default the non-PIC objects would fail to
        # link with R_AARCH64_ADR_PREL_PG_HI21 relocation errors.
        cflags = "-W -Wall -O3 -fPIC"
        # R9: single job, a parallel make needs a jobserver fifo that HMDFS
        # refuses to create.
        self.run(f'make -j1 CC="{cc}" CFLAGS="{cflags}"')
        self.run(
            f'make install DESTDIR="{self.package_folder}" PREFIX=/ '
            f'CC="{cc}" CFLAGS="{cflags}"'
        )

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Tools-only package: libfreeaptx.so, freeaptx.h and libfreeaptx.pc
        # belong to the libfreeaptx package - drop them so that no file ever
        # has two owners (patch 0001 already stops installing them).
        for name in ("include", "lib", "share"):
            path = os.path.join(self.package_folder, name)
            if os.path.isdir(path):
                rmdir(self, path)
        bindir = os.path.join(self.package_folder, "bin")
        for tool in ("freeaptxenc", "freeaptxdec"):
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise ConanException(
                    f"{tool} was not installed - the Makefile relink patch "
                    "(0001) did not take effect"
                )
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS only loads ELF binaries that carry a valid .codesign
        # section; llvm-objcopy/binary-sign-tool ship in the OHOS SDK.
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if not self._is_elf(path):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=path
                )
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=path
                )
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.libs = []