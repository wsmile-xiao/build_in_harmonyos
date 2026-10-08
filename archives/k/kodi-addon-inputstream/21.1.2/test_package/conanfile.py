#!/usr/bin/env python3
"""Conan test_package for kodi-addon-inputstream 21.1.2 — consumer-side check.

The add-on is a Kodi-host-loaded module without a standalone entry point, so
the test loads the packaged module (and its Widevine ssd_wv helper module)
with dlopen() and drives the Kodi 21 binary add-on C ABI exactly like a
minimal host: dlsym of the ADDONCREATOR exports (ADDON_GetTypeVersion /
ADDON_GetTypeMinVersion / ADDON_Create), a real create_instance() declaration
of the CInputStreamAdaptive instance through the stable C ABI factory,
GetCapabilities assertion (IDEMUX|IPOSTIME|IDISPLAYTIME|SEEK|PAUSE|ICHAPTER),
a session-less Close no-op, and clean destroy/destroy_instance/dlclose.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KodiAddonInputstreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Location of the packaged modules, passed to the test command.
        toolchain.variables["ADDON_LIB_DIR"] = \
            self.dependencies["kodi-addon-inputstream"].cpp_info.libdirs[0]
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built inputstream add-on consumer cannot run on this host")
            return
        lib_dir = self.dependencies["kodi-addon-inputstream"].cpp_info.libdirs[0]
        addon_so = os.path.join(lib_dir, "inputstream.adaptive.so")
        ssd_so = os.path.join(lib_dir, "ssd_wv.so")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_kodi_addon_inputstream")
        self.run('"%s" "%s" "%s"' % (test_bin, addon_so, ssd_so), env="conanrun")
