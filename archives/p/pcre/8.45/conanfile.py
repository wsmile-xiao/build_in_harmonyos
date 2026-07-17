#!/usr/bin/env python3
"""Conan recipe for PCRE (Perl Compatible Regular Expressions) library.

PCRE 8.45 is the last version of the legacy PCRE1 library.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PcreConan(ConanFile):
    name = "pcre"
    version = "8.45"
    description = "Perl Compatible Regular Expressions library (version 1, legacy)"
    license = "BSD-3-Clause"
    homepage = "https://www.pcre.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Fix umask 077 to 022 for HMDFS permission compatibility (E011)
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path, "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pcre", "pcrecpp", "pcreposix"]
