#!/usr/bin/env python3
"""Conan recipe for afpfs-ng 0.8.1 — Autotools (configure + make).

afpfs-ng is a client library for the Apple Filing Protocol (AFP).
It provides libafpclient and command-line tools (afpcmd, afpgetstatus).
License: GPL-2.0
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import re


class AfpfsngConan(ConanFile):
    name = "afpfs-ng"
    version = "0.8.1"
    description = "A client library for the Apple Filing Protocol (AFP)"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/afpfs-ng/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable FUSE (not available on HarmonyOS)
        tc.configure_args.append("--disable-fuse")
        # Disable parallel jobserver (HMDFS does not support mkfifo)
        tc.parallel = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Patch 0008 already fixes umask 077→022 in configure itself,
        # so the generated config.status inherits the correct umask.
        # No manual config.status fix needed when patches are applied before configure.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Headers are not installed by make install; copy manually
        from conan.tools.files import copy
        src_inc = os.path.join(self.source_folder, "include")
        copy(self, "*.h", src=src_inc, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["afpclient"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]