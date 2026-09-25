#!/usr/bin/env python3
"""Conan test_package for kodi-addon-screensaver 21.0.2 — consumer-side check.

The add-on is a Kodi-host-loaded module without a standalone entry point, so
the test loads the packaged module with dlopen() and verifies the Kodi 21
binary add-on entry points (ADDON_Create, ADDON_GetTypeVersion,
ADDON_GetTypeMinVersion) plus the screensaver instance API version reported
through ADDON_GetTypeVersion() against kodi/versions.h of the xbmc 21.3-Omega
SDK.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KodiAddonScreensaverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Location of the packaged module, passed to the test binary/command.
        toolchain.variables["ADDON_LIB_DIR"] = \
            self.dependencies["kodi-addon-screensaver"].cpp_info.libdirs[0]
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built screensaver add-on consumer cannot run on this host")
            return
        addon_so = os.path.join(
            self.dependencies["kodi-addon-screensaver"].cpp_info.libdirs[0],
            "screensaver.asteroids.so")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_screensaver_asteroids")
        self.run("%s %s" % (test_bin, addon_so), env="conanrun")
