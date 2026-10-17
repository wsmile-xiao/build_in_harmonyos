#!/usr/bin/env python3
"""Conan test_package for liboauth2 — L1 smoke test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class Liboauth2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive deps needed because oauth2.h includes their headers directly
        self.requires("jansson/2.15.1.1")
        self.requires("cjose/0.6.2.7")
        self.requires("openssl/3.5.8.1")
        self.requires("libcurl/8.5.0")
        self.requires("pcre2/10.48")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindirs[0], "test_liboauth2")
            self.run(cmd, env="conanrun")
