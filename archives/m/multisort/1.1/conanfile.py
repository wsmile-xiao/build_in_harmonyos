#!/usr/bin/env python3
"""Conan recipe - multisort 1.1

multisort merges several httpd logs in Common Log Format into one
date-ordered log on stdout (Zachary Beane, 1999, GPL-2.0-or-later).

Build system: three-line plain Makefile (`CC = gcc`, `CFLAGS = -Wall -g -O2`,
one rule compiling and linking multisort.c in a single step), no configure,
no install target.

OHOS specifics:
  - Compiler and flags come from Conan's AutotoolsToolchain (R33) and are
    passed as make command-line variables, which override the Makefile's
    hard-coded `CC = gcc`. The rule has no link step of its own, so LDFLAGS
    travel in CFLAGS.
  - patches/0001-multisort.c.patch:
      * line buffer of a fixed 8192 bytes instead of libc BUFSIZ (musl 1024,
        glibc 8192): with BUFSIZ, fgets() splits log lines of 1024+ bytes on
        OHOS and the merge garbles them;
      * `static` on the gperf-generated in_word_set(): as a non-static inline
        function, C99 inline semantics give no external definition, so builds
        without inlining (-O0, Debug) fail with `undefined symbol: in_word_set`;
      * merge sentinel LONG_MAX instead of 900000000 (upstream bug, not
        platform specific): the 1999 sentinel is below every timestamp from
        December 2018 on, the merge then ignores the dates and reads a closed
        FILE.
  - No install target: package() copies the binary into bin/.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class MultisortConan(ConanFile):
    name = "multisort"
    version = "1.1"
    description = "Merge several Common Log Format httpd logs into a single date-ordered log"
    license = "GPL-2.0-or-later"
    homepage = "https://www.xach.com/multisort/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("httpd", "access-log", "common-log-format", "merge")

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
        cc = tc_vars.get("CC") or "cc"
        cflags = " ".join(filter(None, (tc_vars.get("CPPFLAGS"), tc_vars.get("CFLAGS"),
                                        "-Wall", tc_vars.get("LDFLAGS"))))
        self.run(f"make -j1 CC={shlex.quote(cc)} CFLAGS={shlex.quote(cflags)}",
                 cwd=self.source_folder)

    def package(self):
        # The tarball ships no COPYING file; the licence notice is the header of multisort.c
        header = load(self, os.path.join(self.source_folder, "multisort.c")).split("*/", 1)[0]
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), header + "*/\n")
        copy(self, "multisort", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
