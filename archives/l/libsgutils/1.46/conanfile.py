#!/usr/bin/env python3
"""Conan recipe — libsgutils (sg3_utils) 1.46, Autotools build for HarmonyOS PC.

- R26: system-name libraries default to static linking.
- package_info() exposes libsgutils2 plus bin/ (CLI tools, R38).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibsgutilsConan(ConanFile):
    name = "libsgutils"
    version = "1.46"
    description = "SCSI generic (sg) utilities and libsgutils2 library for HarmonyOS PC"
    license = "GPL-2.0-or-later"
    homepage = "https://sg.danny.cz/sg/sg3_utils.html"
    url = "https://github.com/hreinecke/sg3_utils"

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
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["sgutils2"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
