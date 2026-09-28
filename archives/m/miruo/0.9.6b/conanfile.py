#!/usr/bin/env python3
"""Conan recipe for miruo 0.9.6b — KLab terminal-interaction traffic monitor CLI.

miruo is a small tcpdump-class command-line tool by KLab: it sniffs terminal
traffic (telnet/ssh sessions) with libpcap and reports per-window-size
throughput, mainly used to measure remote-terminal responsiveness.

Single binary (miruo.c + lnklist.c), autotools (autoconf 2.67), installs to
sbin/ by default (sbin_PROGRAMS in Makefile.am).

Dependencies:
  - libpcap/1.10.6 (packet capture; published on ohpcd, static lib only in the
    package — libpcap.a — so the resulting miruo binary has NEEDED libc.so only)

OHOS adaptations (patches in conandata.yml):
  - 0001-configure.patch: umask 077 -> umask 022 in the config.status temp-dir
    creation block (E011 — HMDFS forces setgid on directories; `umask 077 &&
    mktemp -d` produces a drwx--S--- dir that is not writable even by its
    owner, so config.status fails with "can't create ./confXXXX/subs1.awk:
    Permission denied").

Notes:
  - autoconf 2.67's AC_PROG_CC probe list (gcc/cc/cl.exe only) does not look
    for clang; the OHOS toolchain sets CC via the profile / AutotoolsToolchain,
    which configure honours — no patch needed.
  - Upstream shipped the 0.9.6b tag WITHOUT regenerating configure: the
    embedded version string is still 0.9.6a, so `miruo -V` reports
    "miruo version 0.9.6a".  This is an upstream packaging defect, recorded
    here and in notes.md; NOT patched (patch must stay minimal).
  - miruo reads /proc/self/statm for its own memory usage; verified present
    and readable on HarmonyOS PC.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class MiruoConan(ConanFile):
    name = "miruo"
    version = "0.9.6b"
    description = "KLab terminal-interaction traffic monitor CLI (tcpdump-class, libpcap-based)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/KLab/miruo"
    url = ""  # CI fills this

    # R38: miruo is a CLI tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        # miruo uses AF_PACKET/packet sockets and /proc — Linux/OHOS only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"miruo only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: use Conan get() with sha256 from conandata
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patches applied after source extraction (E011 umask fix)
        apply_conandata_patches(self)

    def generate(self):
        # Feed -I/-L/-l for libpcap into configure/make
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Upstream installs to sbin/ (sbin_PROGRAMS); conan tools live in bin/
        tc.configure_args.append("--sbindir=${prefix}/bin")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM (E074)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # Install with the bindir-redirecting configure args; upstream installs
        # miruo into sbin/, redirected to bin/ via --sbindir=${prefix}/bin.
        autotools.install()

    def package_info(self):
        # Application type: no libs, bindir for the executable
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
