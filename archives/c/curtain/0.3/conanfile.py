#!/usr/bin/env python3
"""Conan recipe for Curtain 0.3 on HarmonyOS PC (ArkUI native host + ported C core)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CurtainConan(ConanFile):
    name = "curtain"
    version = "0.3"
    package_type = "application"
    description = ("Curtain 0.3 full-screen presentation curtain ported to OHOS PC: "
                   "ArkUI native host window with the upstream drag geometry and scaling "
                   "logic in a C core")
    license = "GPL-3.0-or-later"
    homepage = "https://code.google.com/archive/p/ardesia/"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("curtain/0.3 targets OHOS armv8")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="harmony")
        cmake.build()
        cmake.test()

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses", "curtain"))
        copy(self, "curtain.glade", src=os.path.join(self.source_folder, "desktop"),
             dst=os.path.join(self.package_folder, "share", "curtain", "ui"))
        copy(self, "curtain.png", src=os.path.join(self.source_folder, "desktop", "icons"),
             dst=os.path.join(self.package_folder, "share", "curtain", "ui", "icons"))
        harmony = os.path.join(self.package_folder, "share", "curtain", "harmony")
        copy(self, "*", src=os.path.join(self.source_folder, "harmony"), dst=harmony)
        # Binary assets stay out of the patch pipeline; inject the upstream
        # curtain image into the shipped DevEco project.
        copy(self, "curtain.png", src=os.path.join(self.source_folder, "desktop", "icons"),
             dst=os.path.join(harmony, "project", "entry", "src", "main", "resources",
                              "rawfile"))

    def package_info(self):
        self.cpp_info.libs = ["curtain_core"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
