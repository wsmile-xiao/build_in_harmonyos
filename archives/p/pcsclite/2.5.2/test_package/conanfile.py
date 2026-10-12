#!/usr/bin/env python3
"""Consumer smoke test for pcsclite 2.5.2 (PC/SC SCard* client API).

Test strategy (daemon-less CI environment is expected on OHOS):
  - compile + link against the packaged libpcsclite (validates the deliverable)
  - run SCardEstablishContext/SCardReleaseContext round-trip; without a
    running pcscd the API must return SCARD_E_NO_SERVICE (0x8010001D) —
    an error code is a valid assertion that the library is callable.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PcscliteTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        binary = os.path.join(
            self.build_folder,
            self.cpp.build.bindir,
            "test_pcsc",
        )
        self.run(f'"{binary}"', env="conanrun")
