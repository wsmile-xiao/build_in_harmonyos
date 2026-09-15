#!/usr/bin/env python3
"""Conan test_package — opencsg 1.8.2 L1 consumer verification.

Builds test_opencsg (links the packaged libopencsg and calls its public C++
API) and runs it. The binary is executed directly with the ``conanrun``
environment so the dynamic loader finds the packaged ``libopencsg.so``.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class OpencsgTestConan(ConanFile):
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
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_opencsg: no bindirs, binary was not built")
        exe = os.path.join(bindirs[0], "test_opencsg")
        if not os.path.isfile(exe):
            raise ConanException(f"test_opencsg: binary not found at {exe}")
        # conanrun provides the runtime library paths (LD_LIBRARY_PATH) for the
        # shared OpenCSG library.
        self.run(f'"{exe}"', env="conanrun")
