#!/usr/bin/env python3
"""Conan test_package — libdwarfp 2.1.0 L1 test.

R34: test_package must actually call the tested package's API.
libdwarfp is the DWARF producer (write) library of the libdwarf
project:
- Library verification: find_package(libdwarfp) + target_link_libraries
- API verification: dwarf_producer_init() + dwarf_new_die_a() +
  dwarf_add_AT_name_a() + dwarf_transform_to_disk_form_a() +
  dwarf_get_section_bytes_a() + dwarf_producer_finish_a()
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        # Cross-compilation guard: on OHOS aarch64 cross-compile, the test
        # binary cannot run on the x86_64 host, so skip runtime test.
        if not can_run(self):
            return

        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(bin_path, env="conanrun")
