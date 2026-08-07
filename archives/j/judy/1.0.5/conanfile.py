#!/usr/bin/env python3
"""Conan recipe — Judy 1.0.5 (Autotools).

Judy is a high-performance dynamic array library implementing
Judy1, JudyL, JudySL, and JudyHS data structures.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JudyConan(ConanFile):
    name = "judy"
    version = "1.0.5"
    description = "High-performance dynamic array library (Judy1/JudyL/JudySL/JudyHS)"
    license = "LGPL-2.1"
    homepage = "https://judy.sourceforge.net/"
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
        autotools = Autotools(self)
        autotools.configure()
        # Create man/man3 dir in build folder for doc build (out-of-tree)
        man3_dir = os.path.join(self.build_folder, "doc", "man", "man3")
        os.makedirs(man3_dir, exist_ok=True)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["Judy"]
        self.cpp_info.set_property("cmake_file_name", "judy")
        self.cpp_info.set_property("cmake_target_name", "judy::judy")
