#!/usr/bin/env python3
"""Conan test_package — libinput 1.26.2 L1 test.

Compiles and runs a C program that links the installed libinput and calls the
real public API (libinput_path_create_context / libinput_log_set_priority /
libinput_path_add_device / libinput_unref), verifying headers, linking and
runtime behaviour.

The path-based backend is used on purpose: it needs neither udev nor
/dev/uinput, both of which are unavailable in this environment.  The upstream
litest suite (which does need /dev/uinput) is therefore not run — see
../notes.md for the measured reason.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibinputTestConan(ConanFile):
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
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libinput" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
