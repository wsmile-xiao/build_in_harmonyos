#!/usr/bin/env python3
"""Conan recipe for ngrep — a pcap-based network grep tool.

ngrep uses libpcap for packet capture and pcre2 for regex matching.
It is a command-line application (not a library), producing a single binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NgrepConan(ConanFile):
    name = "ngrep"
    version = "1.49.0"
    description = "Network grep - a pcap-based tool that allows you to specify an extended regular or hexadecimal expression to match against data payloads of packets"
    license = "custom"
    homepage = "https://ngrep.sourceforge.net/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")
        self.requires("pcre2/10.45")

    def layout(self):
        basic_layout(self)
        # ngrep uses in-source build (Makefile expects source files in same dir)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # ngrep's configure uses --with-pcap-includes to locate pcap headers
        # (it does NOT use CPPFLAGS for pcap discovery)
        pcap_pkg = self.dependencies["libpcap"].package_folder
        tc.configure_args.append(f"--with-pcap-includes={pcap_pkg}/include")
        tc.configure_args.append("--enable-pcre2")
        tc.configure_args.append("--enable-ipv6")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HarmonyOS: /tmp is read-only and umask 077 causes Permission denied
        # Ensure TMPDIR points to a writable directory
        if not os.environ.get("TMPDIR"):
            os.environ["TMPDIR"] = os.path.join(os.path.expanduser("~"), "tmp")
        # AutotoolsToolchain doesn't auto-add dependency lib/include paths
        # to LDFLAGS/CPPFLAGS; set them explicitly for AC_CHECK_LIB to find -lpcap
        pcap_pkg = self.dependencies["libpcap"].package_folder
        pcre2_pkg = self.dependencies["pcre2"].package_folder
        os.environ["LDFLAGS"] = f"-L{pcap_pkg}/lib -L{pcre2_pkg}/lib"
        os.environ["CPPFLAGS"] = f"-I{pcre2_pkg}/include"
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # ngrep is a command-line tool — expose bindirs for consumers
        self.cpp_info.bindirs = ["bin"]
