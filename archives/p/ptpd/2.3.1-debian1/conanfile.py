#!/usr/bin/env python3
"""Conan recipe for ptpd 2.3.1-debian1 - Precision Time Protocol (IEEE 1588) daemon.

Upstream ships a *generated* autotools tree (configure + Makefile.in), so the
recipe runs that shipped configure instead of regenerating it with autoreconf.

OpenHarmony (bionic) notes, all reproduced on the device:

* Conan only emits --build/--host when it detects cross-building; here host and
  build are both OHOS, so it emits neither and configure would fall back to the
  bundled config.guess, which cannot name bionic. We pass an explicit non-cross
  triplet (aarch64-unknown-linux-gnu) so config.guess is never consulted, while
  $host still matches configure.ac's ``*linux*`` branch used for the
  SO_TIMESTAMPING header probe.
* ``configure`` runs under ``umask 077``; HMDFS (the writable HomeArea) does not
  honour that mode, so config.status cannot create its temp files. Rewrite the
  umask to 022 before configuring (same fix as numactl).
* Two source patches: the <linux/socket.h> vs <sys/socket.h> sockaddr_storage
  redefinition, and bionic's missing ether_ntohost().
* bionic has <utmpx.h> but no setutxent()/pututxline()/endutxent(); disable the
  utmp/utmpx login bookkeeping with configure cache variables (the classic
  utmp path is left disabled too, which is fine for a daemon).

SNMP is disabled (no net-snmp in the archive). libpcap is an optional feature
(upstream --disable-pcap); it stays enabled by default to match Debian.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PtpdConan(ConanFile):
    name = "ptpd"
    version = "2.3.1-debian1"
    description = "PTPd: Precision Time Protocol daemon (IEEE 1588)"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/ptpd/"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/p/ptpd/2.3.1-debian1"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"pcap": [True, False]}
    default_options = {"pcap": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        if self.options.pcap:
            self.requires("libpcap/1.10.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--disable-snmp")
        # bionic declares <utmpx.h> but lacks setutxent/pututxline/endutxent.
        tc.configure_args.append("ac_cv_header_utmpx_h=no")
        tc.configure_args.append("ac_cv_header_utmp_h=no")
        if not self.options.pcap:
            tc.configure_args.append("--disable-pcap")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS ignores the mode bits of mktemp directories created under
        # `umask 077`, so config.status fails to create its temp files.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
