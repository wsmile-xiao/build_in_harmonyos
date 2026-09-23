#!/usr/bin/env python3
"""Consumer-side API test for tiny-aes (L1 official Conan test).

Builds and runs a real C consumer against the packaged library: it includes the
packaged aes.h, links libtiny-aes, and verifies the published FIPS-197 /
NIST SP 800-38A vectors plus the mode semantics that the package claims to
support. The consumer refuses to count a host-only build as OHOS validation.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TinyAesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
            self.output.info(
                "Cross build: the tiny-aes consumer was built but not "
                "executed here; run it on the HarmonyOS PC target."
            )
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_tiny_aes")
        self.run(executable, env="conanrun")
