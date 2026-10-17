#!/usr/bin/env python3
"""Conan recipe for libsixel — Sixel graphics encoding library.

Build system: Meson
Upstream: https://github.com/libsixel/libsixel

All optional features enabled (no trimming): gd, gdk-pixbuf2, libcurl,
jpeg, png. Python bindings disabled (not applicable in Conan context).
Static linking default (OHOS dynamic linker limitation with LD_LIBRARY_PATH).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibsixelConan(ConanFile):
    name = "libsixel"
    version = "1.10.5"
    description = "Sixel graphics encoding library"
    license = "MIT"
    homepage = "https://github.com/libsixel/libsixel"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libjpeg/10")
        self.requires("libpng/1.6.58")
        self.requires("gd/2.3.3.2")
        self.requires("curl/8.15.0")
        self.requires("gdk-pixbuf/2.44.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Enable ALL optional features (no trimming)
        tc.project_options["gdk-pixbuf2"] = "enabled"
        tc.project_options["gd"] = "enabled"
        tc.project_options["libcurl"] = "enabled"
        tc.project_options["jpeg"] = "enabled"
        tc.project_options["png"] = "enabled"
        tc.project_options["python"] = "disabled"
        tc.project_options["tests"] = "disabled"
        # Build shared/static based on Conan option
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # OHOS: meson's subprocess can't find llvm-ar via PATH,
        # so explicitly set archiver path in the meson native file
        if self.settings.os in ("Linux", "OHOS"):
            ar_path = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
            ranlib_path = shutil.which("llvm-ranlib") or "/data/service/hnp/bin/llvm-ranlib"
            if os.path.exists(ar_path):
                os.environ["AR"] = ar_path
            if os.path.exists(ranlib_path):
                os.environ["RANLIB"] = ranlib_path
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["sixel"]
        self.cpp_info.set_property("cmake_file_name", "libsixel")
        self.cpp_info.set_property("cmake_target_name", "libsixel::libsixel")
        self.cpp_info.set_property("pkg_config_name", "libsixel")
