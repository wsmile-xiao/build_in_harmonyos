#!/usr/bin/env python3
"""Conan recipe — cgif 0.5.2 (Meson)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CgifConan(ConanFile):
    name = "cgif"
    version = "0.5.2"
    description = "A fast and lightweight GIF encoder library"
    license = "MIT"
    homepage = "https://github.com/dloebl/cgif"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        # Inject ar into meson native file (profile doesn't set tools.build:archiver)
        native_file = self.generators_folder + "/conan_meson_native.ini"
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =",
            "[binaries]\nar = '/data/service/hnp/bin/ar'\nc ="
        )
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
        self.cpp_info.libs = ["cgif"]
