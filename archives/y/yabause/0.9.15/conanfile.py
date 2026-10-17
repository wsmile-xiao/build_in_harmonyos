#!/usr/bin/env python3
"""Conan recipe — yabause 0.9.15 (Sega Saturn emulator core library).

Upstream builds a static core library (libyabause.a) with CMake but
registers NO install() rules, so packaging is done manually.
Frontends (qt/gtk/sdl/cocoa/runner) are skipped: their deps
(SDL2/OpenGL/Qt/GTK/lodepng) are not available, so we deliver the
emulation core as a library package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class YabauseConan(ConanFile):
    name = "yabause"
    version = "0.9.15"
    description = "yabause — Sega Saturn emulator core library (OHOS port)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Yabause/yabause"
    url = "https://github.com/Yabause/yabause"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Minimal deps: disable optional frontends/features (R1)
        tc.variables["YAB_WANT_MPEG"] = "OFF"
        tc.variables["YAB_WANT_SDL"] = "OFF"
        tc.variables["YAB_WANT_OPENAL"] = "OFF"
        tc.variables["YAB_WANT_OPENGL"] = "OFF"
        tc.variables["YAB_WANT_C68K"] = "OFF"
        tc.variables["YAB_WANT_MUSASHI"] = "ON"
        tc.variables["YAB_USE_SSF"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream has no install() rules; package lib + headers manually.
        build_dir = os.path.join(self.build_folder, "src")
        copy(self, "libyabause.a", src=build_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        src_dir = os.path.join(self.source_folder, "src")
        for sub in ("", "titan", "tsunami", "aosdk", "musashi", "c68k"):
            copy(self, "*.h", src=os.path.join(src_dir, sub),
                 dst=os.path.join(self.package_folder, "include", "yabause", sub), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["yabause"]
        self.cpp_info.includedirs = ["include/yabause"]
        self.cpp_info.bindirs = []
