#!/usr/bin/env python3
"""Conan recipe for colorized-logs 2.7 — ANSI/terminal color filter CLI tools.

Build: CMake. Produces ansi2html, ansi2txt, ttyrec2ansi, pipetty and the
lesstty symlink (console CLI tools). Adapted for HarmonyOS OHOS
(aarch64-unknown-linux-ohos). This is an application package (R38: CLI).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ColorizedLogsConan(ConanFile):
    name = "colorized-logs"
    version = "2.7"
    description = "colorized-logs — tools for colorizing / decoding terminal output (ansi2html, ansi2txt, ttyrec2ansi, pipetty)"
    license = "MIT"
    homepage = "https://github.com/kilobyte/colorized-logs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # lesstty is created as a symlink by the CMake custom target; ensure it
        # is present in the package bin dir (install(TARGETS) copies it).
        bin_dir = os.path.join(self.package_folder, "bin")
        if not os.path.islink(os.path.join(bin_dir, "lesstty")):
            link = os.path.join(bin_dir, "lesstty")
            if not os.path.exists(link) and os.path.exists(os.path.join(bin_dir, "pipetty")):
                os.symlink("pipetty", link)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]