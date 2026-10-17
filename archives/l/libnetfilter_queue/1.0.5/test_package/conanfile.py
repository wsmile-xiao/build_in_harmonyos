#!/usr/bin/env python3
"""Conan test_package — libnetfilter_queue 1.0.5 L1 test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibnetfilterQueueTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries —
        # wrap binary execution with bash (same pattern as libmnl test_package).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        exe = os.path.join(self.build_folder, "test_libnetfilter_queue")
        self.run('{} -c "{}"'.format(bash, exe), env="conanrun")
