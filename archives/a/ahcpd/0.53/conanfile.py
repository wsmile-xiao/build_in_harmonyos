#!/usr/bin/env python3
"""Conan recipe for ahcpd 0.53.

ahcpd is the Ad-Hoc Configuration Protocol daemon. Upstream ships a small
plain Makefile; it respects CC/CFLAGS/LDFLAGS and installs via TARGET+PREFIX.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class AhcpdConan(ConanFile):
    name = "ahcpd"
    version = "0.53"
    description = "Ad-Hoc Configuration Protocol daemon"
    license = "MIT"
    homepage = "https://www.irif.fr/~jch/software/ahcp/"
    url = "https://github.com/jech/ahcpd"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run(
            f'make install TARGET="{self.package_folder}" PREFIX="/usr/local"',
            cwd=self.source_folder,
            env="conanbuild",
        )
        copy(
            self,
            "LICENCE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = [os.path.join("usr", "local", "bin")]
