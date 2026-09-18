#!/usr/bin/env python3
"""Conan test_package — libusbsio 2.1.13 L1 consumer test.

Builds and runs a C program against the installed libusbsio package.
The library targets physical NXP LPC-Link2 / MCU-Link USB-HID bridge
devices which the CI sandbox does not have; per the platform testing
policy the test therefore asserts:
  - full public API surface is linkable and callable
  - version string contract (NXP LIBUSBSIO v2.1c — the exact C library
    revision NXP ships inside the official PyPI libusbsio 2.1.13 wheel)
  - device enumeration path (udev via libudev-zero) returns 0 ports
    cleanly on a machine with no USBSIO hardware
  - error-string contract

Device-bound transfer tests (I2C/SPI/GPIO against a real probe) are
declared out of scope for CI — see the equivalence and scope notes in
the version notes.md.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibusbsioTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _build_environment(self):
        # Same whitespace-corrupted "/system/lib64" entry workaround as
        # used by sibling recipes: prepend a clean /system/lib64 so host
        # tools resolve libc++_shared.so inside the conan build env.
        environment = Environment()
        if self.settings.os == "OHOS" and os.path.isdir("/system/lib64"):
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return environment

    def build(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        bindir = self.cpp.build.bindirs[0]
        smoke = os.path.join(bindir, "test_libusbsio" + suffix)
        suite = os.path.join(bindir, "test_upstream_suite" + suffix)
        with self._build_environment().vars(self).apply():
            self.run(f'"{smoke}"', env="conanrun", cwd=self.build_folder)
            # Upstream Python suite (52 unittest cases) ported to C —
            # see test_upstream_suite.c header for the case mapping and
            # the on-device dlopen limitation rationale.
            self.run(f'"{suite}"', env="conanrun", cwd=self.build_folder)
