#!/usr/bin/env python3
"""Conan test_package for kodi-addon-imagedecoder 21.0.2 — consumer-side check.

The add-on is a Kodi-host-loaded module without a standalone entry point, so
the test loads the packaged module with dlopen() and verifies the Kodi 21
binary add-on entry points (ADDON_Create, ADDON_GetTypeVersion,
ADDON_GetTypeMinVersion) plus the image decoder instance API version reported
through ADDON_GetTypeVersion() against kodi/versions.h of the xbmc 21.3-Omega
SDK.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KodiAddonImagedecoderTestConan(ConanFile):
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
            self.dependencies["kodi-addon-imagedecoder"].cpp_info.libdirs[0]
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built image decoder add-on consumer cannot run on this host")
            return
        addon_so = os.path.join(
            self.dependencies["kodi-addon-imagedecoder"].cpp_info.libdirs[0],
            "imagedecoder.mpo.so")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_imagedecoder_mpo")
        # The module is dlopen()ed, so its own DT_NEEDED shared dependencies
        # (conan-provided libjpeg-turbo / tinyxml2) must be resolvable by the
        # loader at dlopen time — prepend their package lib dirs explicitly
        # instead of relying on the run environment's default collection.
        dep_libdirs = [self.dependencies[dep].cpp_info.libdirs[0]
                       for dep in ("libjpeg-turbo", "tinyxml2")]
        env_prefix = "LD_LIBRARY_PATH=%s" % ":".join(dep_libdirs + ["$LD_LIBRARY_PATH"])
        self.run("%s %s %s" % (env_prefix, test_bin, addon_so), env="conanrun")
