#!/usr/bin/env python3
"""Conan recipe for lzlib — LZMA compression library for the lzip format."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LzlibConan(ConanFile):
    name = "lzlib"
    version = "1.15"
    description = "LZMA compression library for the lzip format"
    license = "GPL-2.0+"
    homepage = "https://www.nongnu.org/lzip/lzlib.html"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("lzlib is supported only on Linux/OHOS")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # lzlib uses a custom configure script (not standard autotools).
        # The script sets CC=gcc by default, overriding environment CC.
        # Pass CC explicitly as a configure argument to use the Conan profile compiler.
        cc = str(self.settings.compiler)
        tc.configure_args.append(f"CC={cc}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebang for HarmonyOS (/bin/sh -> /system/bin/sh)
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path, "#!/bin/sh", "#!/system/bin/sh", strict=False)
        replace_in_file(self, configure_path, "#! /bin/sh", "#! /system/bin/sh", strict=False)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lz"]
