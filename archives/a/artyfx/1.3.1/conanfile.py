#!/usr/bin/env python3
"""Conan recipe for ArtyFX 1.3.1 — LV2 audio plugin collection.

Build system: CMake
Products: artyfx.so (DSP shared library, LV2 plugin)
License: GPL-2.0
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class ArtyfxConan(ConanFile):
    name = "artyfx"
    version = "1.3.1"
    description = "LV2 audio plugin collection (audio effects suite)"
    license = "GPL-2.0"
    homepage = "https://github.com/openAVproductions/openAV-ArtyFX"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lv2/1.18.11-git")
        # cairo needed for GUI build (currently disabled on OHOS due to no X11)
        # self.requires("cairo/1.18.4")
        # libsndfile not yet published on ohpcd; recording feature disabled

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate pkg-config .pc files for cmake's pkg_check_modules
        pkg = PkgConfigDeps(self)
        pkg.generate()

        tc = CMakeToolchain(self)
        # arm64 doesn't support SSE
        tc.variables["BUILD_SSE"] = False
        # GUI disabled: X11 not available on OHOS
        tc.variables["BUILD_GUI"] = False
        tc.variables["BUILD_BENCH"] = False
        # CMake compatibility for old cmake_minimum_required
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMake doesn't recognize "HarmonyOS"; use Linux (OHOS is Linux-based)
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def _create_lv2_compat_symlinks(self):
        """Create LV2 header path compatibility symlinks.
        New LV2 (1.18+) uses lv2/core/lv2.h, old code uses lv2/lv2plug.in/ns/lv2core/lv2.h
        """
        try:
            dep = self.dependencies["lv2"]
            pkg_folder = dep.package_folder
        except (KeyError, AttributeError):
            return
        if not pkg_folder:
            return
        lv2_inc = os.path.join(pkg_folder, "include", "lv2")
        if not os.path.exists(os.path.join(lv2_inc, "core", "lv2.h")):
            return
        compat_base = os.path.join(lv2_inc, "lv2plug.in", "ns")
        os.makedirs(compat_base, exist_ok=True)
        # lv2core -> ../../core
        link = os.path.join(compat_base, "lv2core")
        if not os.path.exists(link):
            os.symlink("../../core", link)
        # ext -> ../.. (maps ext/atom to lv2/atom, ext/urid to lv2/urid, etc.)
        link = os.path.join(compat_base, "ext")
        if not os.path.exists(link):
            os.symlink("../..", link)
        # extensions/ui -> ../../../ui
        ext_dir = os.path.join(compat_base, "extensions")
        os.makedirs(ext_dir, exist_ok=True)
        link = os.path.join(ext_dir, "ui")
        if not os.path.exists(link):
            os.symlink("../../../ui", link)

    def build(self):
        apply_conandata_patches(self)
        self._create_lv2_compat_symlinks()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # artyfx.so is an LV2 plugin, installed to lib/lv2/artyfx.lv2/
        self.cpp_info.libs = ["artyfx"]
        self.cpp_info.libdirs = ["lib/lv2/artyfx.lv2"]
        self.cpp_info.exelinkflags = ["-lpthread"]
