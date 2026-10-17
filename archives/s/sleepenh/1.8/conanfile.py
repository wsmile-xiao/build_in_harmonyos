#!/usr/bin/env python3
"""Conan recipe - sleepenh 1.8

sleepenh is an enhanced sleep(1) for shell loops that must repeat at a fixed
interval without cumulative drift: it prints the absolute end time of every
sleep, and the next call can take that value as its starting point
(GPL-2.0-or-later; Pedro Zorzenon Neto 2003, Nicolas Schier 2014-2024).

Build system: small plain Makefile (`CC = gcc`,
`CFLAGS = -std=gnu11 -Wall -Wextra -O2 $(EXTRA_CFLAGS)`, GNU make's implicit
`%: %.c` rule), no configure; the version string comes from `git describe`.

OHOS specifics:
  - Compiler and flags come from Conan's AutotoolsToolchain (R33) and are
    passed as make command-line variables: CC overrides the hard-coded gcc,
    the toolchain CFLAGS go through the upstream EXTRA_CFLAGS hook (a
    command-line CFLAGS would also discard the target-specific
    -DVCSVERSION), CPPFLAGS and LDFLAGS reach the implicit link rule directly.
  - `vcsversion` is set on the make command line, as Debian's rules file does:
    the source archive has no .git, so `git describe` would leave the version
    string empty (`sleepenh ` instead of `sleepenh 1.8`).
  - Only the `sleepenh` target is built; the man page is packaged as is
    instead of through the `sleepenh.1.gz` rule, so no gzip is needed.
  - patches/0001-sleepenh.c.patch: usage() printed glibc's
    program_invocation_short_name, which the OHOS musl headers do not declare
    (compile error) and libc.so does not export; the name is now taken from
    argv[0] (basename, the value glibc provides). No platform macro.
  - The upstream install target writes to $(DESTDIR)/usr/...; package()
    copies the binary and the man page into the Conan layout instead.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SleepenhConan(ConanFile):
    name = "sleepenh"
    version = "1.8"
    description = "Enhanced sleep that can sleep until an absolute time, for drift-free periodic shell loops"
    license = "GPL-2.0-or-later"
    homepage = "https://codeberg.org/nsc/sleepenh"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("sleep", "timer", "shell", "command-line")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # Pure C program
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # R32: OHOS is a supported Linux-like target
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux and OHOS only")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler and flags from the Conan toolchain, never bare shell variables
        tc_vars = AutotoolsToolchain(self).vars()
        make_vars = {
            "CC": tc_vars.get("CC") or "cc",
            "EXTRA_CFLAGS": tc_vars.get("CFLAGS", ""),
            "CPPFLAGS": tc_vars.get("CPPFLAGS", ""),
            "LDFLAGS": tc_vars.get("LDFLAGS", ""),
            # Upstream derives the version from `git describe`; the archive has no .git
            "vcsversion": f'\\"{self.version}\\"',
        }
        args = " ".join(f"{key}={shlex.quote(value)}" for key, value in make_vars.items())
        self.run(f"make -j1 {args} sleepenh", cwd=self.source_folder)

    def package(self):
        # The archive ships no COPYING file; the licence notice is the header of sleepenh.c
        header = load(self, os.path.join(self.source_folder, "sleepenh.c")).split("*/", 1)[0]
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), header + "*/\n")
        copy(self, "sleepenh", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "sleepenh.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
