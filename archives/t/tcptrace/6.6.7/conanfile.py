#!/usr/bin/env python3
"""Conan recipe for tcptrace 6.6.7 (Autotools)."""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class TcptraceConan(ConanFile):
    name = "tcptrace"
    version = "6.6.7"
    package_type = "application"

    description = "A TCP dump file analysis tool"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/blitz/tcptrace"
    topics = ("network", "tcp", "packet-analysis")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # E002: /tmp is read-only on OHOS, redirect TMPDIR to build folder
        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        # Regenerate bison/flex output with modern tools (replaces patches 0005-0007)
        env.define("YACC", "bison -y")
        env.define("LEX", "flex")
        # Old autotools (2.52) Makefile.in hardcodes PCAP_INCS paths and
        # CFLAGS doesn't include $(CPPFLAGS), so Conan's dependency include
        # paths never reach the compiler. Pass them via CFLAGS/LDFLAGS/LIBS
        # which configure propagates to V_CCOPT and the link rule.
        libpcap = self.dependencies["libpcap"]
        inc_flags = " ".join(f"-I{d}" for d in libpcap.cpp_info.includedirs)
        env.append("CFLAGS", inc_flags)
        lib_flags = " ".join(f"-L{d}" for d in libpcap.cpp_info.libdirs)
        env.append("LDFLAGS", lib_flags)
        env.append("LIBS", "-lpcap")
        envvars = env.vars(self)
        envvars.save_script("tcptrace_env")

    def build(self):
        os.makedirs(os.path.join(self.build_folder, "tmp"), exist_ok=True)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
