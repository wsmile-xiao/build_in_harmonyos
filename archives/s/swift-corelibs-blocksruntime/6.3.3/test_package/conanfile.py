#!/usr/bin/env python3
"""Consumer tests for swift-corelibs-blocksruntime 6.3.3."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.layout import basic_layout


class SwiftCorelibsBlocksRuntimeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    test_executables = (
        "test_global_block",
        "test_captured_block",
        "test_escape_lifetime",
        "test_byref_capture",
        "test_nested_block",
        "test_retain_release",
        "test_block_metadata",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.extra_cflags.append("-fblocks")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            for executable in self.test_executables:
                self.run(f"./{executable}", env="conanrun")
