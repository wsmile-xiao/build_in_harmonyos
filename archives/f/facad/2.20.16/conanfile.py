#!/usr/bin/env python3
"""Conan recipe for facad 2.20.16 — Meson build system.

facad is a modern, colorful directory listing tool for the command line.
It provides emoji-based file type representation, sorted output with
directories first, long listing format, and directory analytics.

Pure C implementation with no external dependencies (only libc and libm).
Builds an executable binary via meson + ninja.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class FacadConan(ConanFile):
    name = "facad"
    version = "2.20.16"
    description = "Modern colorful directory listing tool for the command line"
    license = "MIT"
    homepage = "https://github.com/yellow-footed-honeyguide/facad"

    package_type = "application"

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
        tc = MesonToolchain(self)
        tc.generate()
        # Inject ar into meson native file (profile doesn't set tools.build:archiver)
        ar_path = shutil.which("ar")
        if not ar_path:
            raise RuntimeError("ar not found in PATH")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file) as f:
            content = f.read()
        old_content = content
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc ="
        )
        if content == old_content:
            raise RuntimeError("Failed to inject ar into meson native file "
                               "(pattern '[binaries]\\nc =' not found)")
        with open(native_file, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
