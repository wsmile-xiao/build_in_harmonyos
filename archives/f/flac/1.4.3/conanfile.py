#!/usr/bin/env python3
"""Conan recipe — FLAC (Free Lossless Audio Codec).

Build system: Autotools (configure + make)
Dependencies: libogg/1.3.5
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FlacConan(ConanFile):
    name = "flac"
    version = "1.4.3"
    description = "Free Lossless Audio Codec — lossless audio compression library and tools"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/flac/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libogg/1.3.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Pass libogg install prefix to flac's XIPH_PATH_OGG macro
        ogg = self.dependencies["libogg"]
        tc.configure_args.append(f"--with-ogg={ogg.package_folder}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix mktemp issue in configure script (E002: /tmp read-only on OHOS)
        # config.status uses mktemp -d "./confXXXXXX" which creates dirs in CWD,
        # but HMDFS doesn't allow this on OHOS
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(
                self, configure_path,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp="${TMPDIR:-/tmp}/conan-cs-$$"',
            )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.components["flac"].libs = ["FLAC"]
        self.cpp_info.components["flac"].requires = ["libogg::libogg"]
        self.cpp_info.components["flac++"].libs = ["FLAC++"]
        self.cpp_info.components["flac++"].requires = ["flac"]
