#!/usr/bin/env python3
"""Conan recipe for rephrase 0.2 -- passphrase recovery tool for GnuPG / Cryptsetup-LUKS.

Upstream = a single C translation unit (rephrase.c) plus a hand-written Makefile.
Zero external library dependencies (the Makefile declares no LDLIBS / LIBS / LDFLAGS);
only libc + termios + mlock(2) + fork/execv/waitpid.

Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos, musl).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RephraseConan(ConanFile):
    name = "rephrase"
    version = "0.2"
    description = ("rephrase - specialized passphrase recovery tool for GnuPG and "
                   "Cryptsetup/LUKS: retries every combination of the passphrase "
                   "alternatives the user still remembers")
    license = "GPL-3.0-only"
    homepage = "https://www.roguedaemon.net/rephrase/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

        # R33: take the compiler from Conan conf, never from bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = (compilers or {}).get("c", "clang")

        # Upstream Makefile carries the mandatory version macro itself:
        #   DEFS = -DVERSION="$(version)" ... ; CPPFLAGS += $(DEFS)
        # and rephrase.c does #ifndef VERSION -> #error.  So ONLY CC is overridden on
        # the make command line; touching CFLAGS/CPPFLAGS would risk dropping DEFS.
        # GPG / CRYPTSETUP / PATTERN_MAX / ARGS_MAX stay at upstream defaults.
        # R9: always -j1 (GNU make jobserver FIFO is unreliable on HMDFS).
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Upstream `make install` must run as root and does:
        #   ./install-sh -c -o 0 -g 0 -m 4711   (binmode = 4711 == setuid root)
        # That is neither possible nor desirable inside a package, so the ELF is
        # copied here at plain 0755.  See notes.md for why this is still functional
        # on OHOS (RLIMIT_MEMLOCK is unlimited => mlock(2) succeeds without setuid).
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "rephrase", self.source_folder, bindir)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        target = os.path.join(bindir, "rephrase")
        if os.path.isfile(target):
            os.chmod(target, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
