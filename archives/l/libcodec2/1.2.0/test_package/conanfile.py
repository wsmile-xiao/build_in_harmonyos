#!/usr/bin/env python3
"""Conan test_package — codec2 L1 consumer test."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class Codec2TestConan(ConanFile):
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
        qemu = os.environ.get("OHOS_QEMU")
        runroot = os.environ.get("OHOS_RUNROOT", "")
        if qemu:
            args = [qemu]
            if runroot:
                args += ["-L", runroot]
            self.run(" ".join(args + ["./test_codec2"]), env="conanrun")
            return
        if cross_building(self):
            self.output.info("cross-building: compile and link completed; target execution is deferred")
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_codec2'", env="conanrun")
