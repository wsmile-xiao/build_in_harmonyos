#!/usr/bin/env python3
"""Conan test_package — libidl2 0.8.14 consumer test.

Builds test.c (real libIDL API consumer) and runs it. On OHOS workers the
binary is compiled by the OHOS toolchain, linked against OHOS glib and
executed on HarmonyOS — this is the HarmonyOS-specific consumer validation
(rule12, N>=1). can_run() guards host-vs-target execution for cross builds.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Libidl2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # A macOS dev box simulating the OHOS worker with an OHOS-settings
            # profile cannot execute the OHOS binary (see conanfile.py
            # build_requirements / user.build:flex_bison_native); the real
            # run happens on the OHOS CI worker.
            if self.conf.get("user.build:flex_bison_native", default=False):
                self.output.info(
                    "skip run: local OHOS simulation on macOS cannot execute "
                    "OHOS binaries (run is exercised on the OHOS CI worker)")
                return
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_libidl2"),
                     env="conanrun")
