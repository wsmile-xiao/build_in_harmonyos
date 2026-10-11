#!/usr/bin/env python3
"""Conan test_package for kodi-pvr-iptvsimple 21.11.0 — consumer-side check.

The add-on is a Kodi-host-loaded PVR client module without a standalone entry
point. The test loads the packaged module and verifies (a) the Kodi 21 binary
add-on contract (ADDON_Create / ADDON_GetTypeVersion / ADDON_GetTypeMinVersion
and the PVR instance API version reported against the vendored 21.3-Omega SDK
headers), (b) real functionality through the module's exported FileUtils
decompression helpers (zlib and liblzma paths), and (c) a HarmonyOS-specific
check that the module binds eagerly and resolves zlib against the OHOS system
libz at runtime.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KodiPvrIptvsimpleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Absolute path of the packaged add-on module, handed to the test
        # binaries (they dlopen() it, like the Kodi host does).
        libdir = self.dependencies["kodi-pvr-iptvsimple"].cpp_info.libdirs[0]
        toolchain.variables["ADDON_MODULE"] = os.path.join(libdir, "pvr.iptvsimple.so")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross-built pvr.iptvsimple add-on consumer cannot run on this host")
            return
        module = os.path.join(
            self.dependencies["kodi-pvr-iptvsimple"].cpp_info.libdirs[0],
            "pvr.iptvsimple.so")
        bindir = self.cpp.build.bindirs[0]
        self.run("%s %s" % (os.path.join(bindir, "test_kodi_pvr_iptvsimple"), module),
                 env="conanrun")
        self.run("%s %s" % (os.path.join(bindir, "test_kodi_pvr_iptvsimple_ohos"), module),
                 env="conanrun")
