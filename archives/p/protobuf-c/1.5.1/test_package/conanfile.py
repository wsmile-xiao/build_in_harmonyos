#!/usr/bin/env python3
"""Conan test_package for protobuf-c 1.5.1 — consumer (HarmonyOS-specific) test.

Runs as L1 during `conan create`. It links a consumer against the packaged
libprotobuf-c and drives the runtime API (version reporting, ProtobufCBufferSimple
growth, enum-descriptor lookups) through 14 assertions.

Upstream's own 11 test programs are executed in the recipe's build() phase via
ctest; see MANIFEST.yml and ../notes.md.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

CONSUMER_TEST = "test_protobuf_c"


class ProtobufcTestConan(ConanFile):
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
        for root, _dirs, files in os.walk(self.build_folder):
            if CONSUMER_TEST in files:
                # Built against the conanbuild environment; nothing to load at run
                # time beyond libc/libm, since the package is a static library.
                self.run(os.path.join(root, CONSUMER_TEST), env="conanrun")
                return
        raise ConanException(CONSUMER_TEST + " was not built")
