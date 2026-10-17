#!/usr/bin/env python3
"""Conan test_package for lcmaps-plugins-voms 1.7.1 — OHOS consumer smoke.

Builds test_lcmaps_plugins_voms (C) linked against the LCMAPS framework and
runs it against the packaged plugin tree. Linking liblcmaps_without_gsi
(NEEDED) reproduces the LCMAPS engine's process image, so the plugins'
lcmaps_log/... relocations resolve exactly as they do in production. See
test.c for the covered adaptation points.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LcmapsPluginsVomsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicit repeat of the transitive framework dependency: CMakeDeps
        # only generates config files for direct requires, and the test links
        # liblcmaps_without_gsi to reproduce the LCMAPS engine process image.
        # Keep in sync with the main recipe's requirements().
        self.requires("lcmaps/1.6.7")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LCMAPS_TEST_ROOT"] = self.dependencies[
            "lcmaps-plugins-voms"
        ].package_folder
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        pkg_path = self.dependencies["lcmaps-plugins-voms"].package_folder
        fw_path = self.dependencies["lcmaps"].package_folder
        # conanrunenv aggregates only the direct require's libdirs on this
        # conan version; set the runtime library path explicitly instead:
        # <framework>/lib for liblcmaps_without_gsi.so.0 and
        # <tested>/lib/lcmaps for the plugin objects.
        ld_path = ":".join([
            os.path.join(fw_path, "lib"),
            os.path.join(pkg_path, "lib", "lcmaps"),
        ])
        # 1. consumer smoke: dlopen/dlsym of every plugin object
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_lcmaps_plugins_voms")
        self.run(
            "LD_LIBRARY_PATH='%s' '%s' '%s'" % (ld_path, bin_path, pkg_path),
            env="conanrun",
        )
        # 2. end-to-end consumer test: full LCMAPS evaluation round trip
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_lcmaps_plugins_voms_e2e")
        self.run(
            "LD_LIBRARY_PATH='%s' '%s' '%s'" % (ld_path, bin_path, pkg_path),
            env="conanrun",
        )
