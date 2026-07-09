#!/usr/bin/env python3
"""Conan recipe for gnu-which 2.25 — Autotools project."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnuwhichConan(ConanFile):
    name = "gnu-which"
    version = "2.25"
    description = "GNU which utility - find full path of shell commands"
    license = "GPL-3.0-or-later"
    homepage = "https://savannah.gnu.org/projects/which/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

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
        # R5: OHOS has no /bin/sh, configure needs bash
        if self.settings.os in ("Linux", "OHOS"):
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
            tc.configure_args.append(f"SHELL={bash}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
