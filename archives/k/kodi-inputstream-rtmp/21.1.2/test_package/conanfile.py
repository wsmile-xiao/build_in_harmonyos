#!/usr/bin/env python3
"""Conan test_package for kodi-inputstream-rtmp 21.1.2.

Consumer-side check: compiles a small client against the built
inputstream.rtmp add-on module (CMakeDeps target), then runs it on the host.
The client calls the C entry points exported by the ADDONCREATOR macro
(kodi/AddonBase.h): ADDON_GetTypeVersion()/ADDON_GetTypeMinVersion() are pure
functions compiled into the add-on that report the Kodi instance API versions
it was built against, so they can be exercised without a Kodi host.
A Kodi-hosted stream session cannot be tested here (no Kodi runtime).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KodiInputstreamRtmpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built inputstream.rtmp consumer cannot run on this host")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_inputstream_rtmp")
        self.run(test_bin, env="conanrun")
