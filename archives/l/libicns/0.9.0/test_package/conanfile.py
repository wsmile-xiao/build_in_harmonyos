#!/usr/bin/env python3
"""Conan test_package for libicns — real consumer API test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/l/libicns/0.9.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibicnsTestConan(ConanFile):
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
        # Run under Conan's generated runtime environment so shared DLLs resolve.
        # Fail closed (alass/aliki precedent): CI builds with host=build=OHOS
        # so can_run() is True there; a False here means a genuine cross
        # build where these binaries cannot execute — skip would be a false
        # green, so refuse instead.
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "libicns test_package must run natively on the target"
            )
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_libicns"), env="conanrun")
        if str(self.settings.os) == "OHOS":
            # HarmonyOS-specific test — counted as its own independent
            # test entry (consumer 1/1 + ohos_specific 1/1).
            self.run(os.path.join(bindir, "test_ohos_libicns"), env="conanrun")
