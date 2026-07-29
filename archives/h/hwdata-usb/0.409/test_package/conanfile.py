#!/usr/bin/env python3
"""Consumer and fault-injection tests for hwdata-usb 0.409."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class HwdataUsbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        if can_run(self):
            executable = os.path.join(
                self.cpp.build.bindirs[0], "test_hwdata_usb"
            )
            self.run(f'"{executable}"', env="conanrun")
            usb_ids = os.path.join(
                self.dependencies["hwdata-usb"].package_folder,
                "share",
                "hwdata",
                "usb.ids",
            )
            self.run(
                f'"{executable}" --expect-missing "{usb_ids}.missing"',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross build: hwdata-usb consumer was built; run both "
                "scenarios with usb.ids on the HarmonyOS PC emulator."
            )
