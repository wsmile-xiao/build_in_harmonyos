#!/usr/bin/env python3
"""Conan recipe — verdigris 1.3 (header-only)

Header-only Qt moc replacement using C++14 constexpr meta-object generation.
Binary compatible with Qt 5.9+ and Qt 6.x, no moc required.
"""

import os

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class VerdigrisConan(ConanFile):
    name = "verdigris"
    version = "1.3"
    description = "Header-only Qt moc replacement — constexpr QMetaObject generation without moc"
    license = "LGPL-3.0-or-later AND GPL-2.0-or-later"
    homepage = "https://github.com/woboq/verdigris"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("qt", "moc", "header-only", "constexpr")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        copy(self, "LICENSE.LGPLv3", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"), dst=os.path.join(self.package_folder, "include", "verdigris"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"), dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "verdigris")
        self.cpp_info.set_property("cmake_target_name", "verdigris::verdigris")
