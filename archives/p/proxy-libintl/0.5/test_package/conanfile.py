#!/usr/bin/env python3
"""Installed-package consumer for proxy-libintl 0.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ProxyLibintlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "NOT_RUN PROXY_LIBINTL_TARGET_CONSUMER=0/1 reason=cross_building"
            )
            return
        test_binary = os.path.join(
            self.cpp.build.bindirs[0], "proxy_libintl_consumer"
        )
        self.run(test_binary, env="conanrun")
