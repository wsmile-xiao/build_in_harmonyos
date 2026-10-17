#!/usr/bin/env python3
"""Conan recipe for the iso-codes 4.20.1 data package."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class IsoCodesConan(ConanFile):
    name = "iso-codes"
    version = "4.20.1"
    description = "ISO country, language, script and currency data"
    license = "LGPL-2.1-or-later"
    homepage = "https://salsa.debian.org/iso-codes-team/iso-codes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        cross_file = os.path.join(
            self.generators_folder, MesonToolchain.cross_filename
        )
        native_file = os.path.join(
            self.generators_folder, MesonToolchain.native_filename
        )
        if os.path.isfile(cross_file):
            machine_arg = '--cross-file "{}"'.format(cross_file)
        elif os.path.isfile(native_file):
            machine_arg = '--native-file "{}"'.format(native_file)
        else:
            raise RuntimeError("MesonToolchain did not generate a machine file")
        self.run(
            'meson setup {} "{}" "{}" --prefix=/'.format(
                machine_arg, self.build_folder, self.source_folder
            ),
            env="conanbuild",
        )
        meson.build()
        self.run(
            'meson test -C "{}" --print-errorlogs --no-rebuild'.format(
                self.build_folder
            ),
            env="conanbuild",
        )

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.define_path("ISO_CODES_PREFIX", self.package_folder)
        self.runenv_info.append_path(
            "PKG_CONFIG_PATH", self.package_folder + "/share/pkgconfig"
        )
