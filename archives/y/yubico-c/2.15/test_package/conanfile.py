#!/usr/bin/env python3
"""Conan test_package for yubico-c 2.15 (ykclient).

Per R34, the test substantively depends on the tested package:
test_package.c includes ykclient.h, links libykclient, and calls real API
functions (ykclient_global_init, ykclient_check_version, ykclient_init,
ykclient_set_client_hex, ykclient_strerror).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class YubicocTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(bin_path, env="conanrun")
