#!/usr/bin/env python3
"""Conan recipe - sredird 2.2.2

sredird is an RFC 2217 ("Telnet Com Port Control Option") serial port
redirector: run from an inetd-style superserver, it exposes a local serial
device to a network client and applies the client's baud rate, data size,
parity and stop bit requests to the device through termios
(GPL-2.0-or-later; InfoTecna s.r.l. 1999-2003, Columbia University 2001-2002).

Build system: one C file and a two-line Makefile (`CC=gcc`, `CFLAGS=-O3 -pipe
-fomit-frame-pointer`, one `$(CC) $(CFLAGS) $(WFLAGS) -o sredird sredird.c`
rule that compiles and links in a single step), no configure.

OHOS specifics:
  - Compiler and flags come from Conan's AutotoolsToolchain (R33) and are
    passed as make command-line variables: CC overrides the hard-coded gcc;
    CFLAGS keeps the upstream optimisation flags and appends the toolchain
    CFLAGS/CPPFLAGS/LDFLAGS (the rule has no separate link line, so the linker
    flags have to travel in CFLAGS).
  - patches/0001-sredird.c.patch (no platform macro):
      1. `#include <termio.h>` is a glibc header that OHOS musl does not ship
         (compile error), and nothing in sredird.c uses it (only <termios.h>
         API is used). The include is removed.
      2. The 4-byte RFC 2217 baud rate field was carried in an `unsigned long`
         (SendBaudRate serialises it with a `sizeof` loop, the SET-BAUDRATE
         handler reads it through a pointer cast). On LP64 (aarch64) that is 8
         bytes and the acknowledgement frame gets 4 extra zero bytes, with no
         compiler warning. It is now a `uint32_t` (<stdint.h> added).
  - The upstream Makefile has no install target; package() copies the binary,
    the man page and the licence into the Conan layout.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SredirdConan(ConanFile):
    name = "sredird"
    version = "2.2.2"
    description = "RFC 2217 compliant Telnet serial port redirector (share a serial port over the network)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.ibiblio.org/pub/linux/system/serial/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("serial", "rfc2217", "telnet", "termios", "command-line")

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
        cflags = " ".join(
            part for part in (
                "-O3 -pipe -fomit-frame-pointer",  # upstream defaults
                tc_vars.get("CPPFLAGS", ""),
                tc_vars.get("CFLAGS", ""),
                tc_vars.get("LDFLAGS", ""),
            ) if part
        )
        make_vars = {"CC": tc_vars.get("CC") or "cc", "CFLAGS": cflags}
        args = " ".join(f"{key}={shlex.quote(value)}" for key, value in make_vars.items())
        self.run(f"make -j1 {args} sredird", cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "sredird", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "sredird.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "sredird"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
