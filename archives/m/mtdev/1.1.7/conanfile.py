#!/usr/bin/env python3
"""Conan recipe for mtdev - Multitouch Protocol Translation Library.

mtdev transforms all variants of kernel MT events to the slotted type B protocol.
"""
from conan import ConanFile
import os

from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MtdevConan(ConanFile):
    name = "mtdev"
    version = "1.1.7"
    description = "Multitouch Protocol Translation Library - transforms all variants of kernel MT events to the slotted type B protocol"
    license = "MIT"
    homepage = "https://bitmath.org/code/mtdev/"

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
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 + mktemp on HMDFS: directories created with umask 077
        # cannot have files written inside them on HarmonyOS HMDFS filesystem.
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path,
                        "umask 077 && mktemp -d",
                        "mktemp -d")
        replace_in_file(self, configure_path,
                        '(umask 077 && mkdir "$tmp")',
                        '(mkdir "$tmp")')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["mtdev"]
