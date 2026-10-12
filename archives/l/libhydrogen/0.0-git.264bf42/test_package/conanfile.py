#!/usr/bin/env python3
"""Conan test_package — libhydrogen 0.0-git.264bf42 (R34 real API consumer test).

The test binary calls the packaged library from a consumer's perspective:
hydro_init, hydro_sign_keygen keypair generation + hydro_sign_create /
hydro_sign_verify roundtrip, tamper rejection, deterministic keygen,
secretbox roundtrip + tamper rejection, hash, kdf, and the incremental
sign state API.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibhydrogenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2 precedent).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()


    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: run the test binary that really exercises the libhydrogen API
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_hydrogen")
            self.run(test_bin, env="conanrun")
        else:
            self.output.info(
                "Cross build: run test_hydrogen on the HarmonyOS target"
            )
