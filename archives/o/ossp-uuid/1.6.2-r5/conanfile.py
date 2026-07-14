#!/usr/bin/env python3
"""Conan recipe for ossp-uuid — Autotools project (configure + make).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir, copy
from conan.tools.layout import basic_layout


class OsspuuidConan(ConanFile):
    name = "ossp-uuid"
    version = "1.6.2-r5"
    description = "OSSP uuid - Universally Unique Identifier library"
    license = "MIT"
    homepage = "http://www.ossp.org/pkg/lib/uuid/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "patches/*.patch",
             src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        with chdir(self, src):
            # E002: HMDFS cannot create temp dirs, pre-create one
            self.run("mkdir -p conf_preset")
            # E001: CC=clang, --no-create to patch config.status after
            self.run("CC=clang CXX=clang++ ./configure "
                     f"--prefix={self.package_folder} "
                     "--enable-static --disable-shared "
                     "--build=aarch64-unknown-linux-ohos "
                     "--no-create")
            self.run("sed -i 's|mktemp -d \"\\./confXXXXXX\"|echo \"./conf_preset\"|' config.status")
            self.run("./config.status")
            self.run("make -j1")
            self.run("make install")

    def package(self):
        pass  # build() already calls make install

    def package_info(self):
        self.cpp_info.libs = ["uuid"]