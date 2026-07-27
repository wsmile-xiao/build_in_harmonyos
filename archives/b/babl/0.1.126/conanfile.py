#!/usr/bin/env python3
"""Conan recipe — babl 0.1.126 (Meson).
Pixel format conversion library, used by GEGL and GNOME image processing.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class BablConan(ConanFile):
    name = "babl"
    version = "0.1.126"
    description = "Pixel format conversion library, used by GEGL and GNOME image processing"
    license = "LGPL-3.0"
    homepage = "https://gegl.org/babl/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Ensure AR points to a discoverable path for meson
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if ar_path:
            os.environ["AR"] = ar_path
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["with-docs"] = "false"
        tc.project_options["enable-gir"] = "false"
        tc.project_options["enable-vapi"] = "false"
        tc.generate()

    def build(self):
        # Ensure meson build tool is available (not pre-installed on all CI workers)
        if not shutil.which("meson"):
            self.run(f"{sys.executable} -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["babl-0.1"]
        self.cpp_info.includedirs = ["include/babl-0.1"]
        self.cpp_info.libdirs = ["lib"]
