#!/usr/bin/env python3
"""Conan recipe - UDPcast 20250223 (Autotools application)."""

import os

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UdpcastConan(ConanFile):
    name = "udpcast"
    version = "20250223"
    description = "UDP multicast file transfer tools"
    license = "GPL-2.0-only AND BSD-2-Clause"
    homepage = "https://udpcast.linux.lu/"
    url = "https://udpcast.linux.lu/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--prefix=/",
            "--sbindir=/bin",
            "--mandir=/share/man",
        ])
        tc.extra_cflags.append("-DBB_FEATURE_UDPCAST_FEC")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args"
        )
        config_shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        build_folder = os.path.abspath(self.build_folder)
        os.environ["PWD"] = build_folder
        self.run(
            f'PWD="{build_folder}" CONFIG_SHELL="{config_shell}" '
            f'"{config_shell}" '
            f'"{configure}" {configure_args}'
        )
        autotools = Autotools(self)
        autotools.make(args=["-j1"])

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        includedir = os.path.join(self.package_folder, "include", "udpcast")
        for program in ("udp-sender", "udp-receiver"):
            copy(self, program, src=self.build_folder, dst=bindir, keep_path=False)
        for manpage in ("udp-sender.1", "udp-receiver.1"):
            copy(self, manpage, src=self.build_folder, dst=mandir, keep_path=False)
        copy(
            self,
            "rateGovernor.h",
            src=self.source_folder,
            dst=includedir,
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
