#!/usr/bin/env python3
"""Conan recipe — libsodium 1.0.20 (Autotools)."""

import glob
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _relax_hmdfs_umask(configure_path):
    """Prevent Autoconf config.status temp directories from failing on HMDFS."""
    path = Path(configure_path)
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace("umask 077", "umask 022"), encoding="utf-8")


class LibsodiumConan(ConanFile):
    name = "libsodium"
    version = "1.0.20"
    description = "A modern, portable, easy-to-use crypto library"
    license = "ISC"
    homepage = "https://libsodium.org"
    url = "https://github.com/jedisct1/libsodium"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported operating system: {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "Shared libsodium has not been verified on HarmonyOS; "
                "use shared=False"
            )

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        managed_arguments = {
            "--disable-shared",
            "--enable-shared",
            "--disable-static",
            "--enable-static",
        }
        toolchain.configure_args = [
            argument
            for argument in toolchain.configure_args
            if str(argument) not in managed_arguments
            and (
                cross_building(self)
                or not str(argument).startswith(("--build=", "--host="))
            )
        ]
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
        toolchain.configure_args.append("--disable-dependency-tracking")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            _relax_hmdfs_umask(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if cross_building(self):
            # Build every official test program; execute them on the OHOS target.
            autotools.make(target="check", args=["-j1", "TESTS="])
        else:
            autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        for libtool_archive in glob.glob(
            os.path.join(self.package_folder, "lib", "*.la")
        ):
            os.remove(libtool_archive)

    def package_info(self):
        self.cpp_info.libs = ["sodium"]
        self.cpp_info.set_property("cmake_file_name", "libsodium")
        self.cpp_info.set_property("cmake_target_name", "libsodium::libsodium")
        self.cpp_info.set_property("pkg_config_name", "libsodium")
