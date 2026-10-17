#!/usr/bin/env python3
"""Conan recipe for the Lomiri sound resource package."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class LomiriSoundsConan(ConanFile):
    name = "lomiri-sounds"
    version = "25.01"
    description = "Notification and ringtone sound resources for Lomiri"
    license = "CC-BY-SA-3.0"
    homepage = "https://gitlab.com/ubports/development/core/lomiri-sounds"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_INSTALL_DATADIR"] = "share"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        data_dir = os.path.join(self.package_folder, "share", "sounds", "lomiri")
        pkgconfig_dir = os.path.join(self.package_folder, "share", "pkgconfig")
        self.buildenv_info.define_path("LOMIRI_SOUNDS_DATA_DIR", data_dir)
        self.buildenv_info.define_path("LOMIRI_SOUNDS_PKGCONFIG_DIR", pkgconfig_dir)
