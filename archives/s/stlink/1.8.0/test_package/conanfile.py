#!/usr/bin/env python3
"""Conan test_package — stlink 1.8.0 consumer test.

Compiles a real consumer program that links against libstlink and calls the
stlink_parse_ihex() API (a pure parser that needs no USB hardware), asserting
the parsed bytes. Also runs the installed `st-info --version` binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class StlinkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        # stlink public headers pull in <libusb.h> via libusb_settings.h, so
        # the consumer must also resolve the libusb dependency package. The
        # libusb/1.0.27 recipe's CMakeDeps data has empty include dirs on this
        # remote, so inject the include path explicitly.
        tc = CMakeToolchain(self)
        try:
            libusb = self.dependencies["libusb"]
            inc = os.path.join(libusb.package_folder, libusb.cpp_info.includedirs[0])
            tc.cache_variables["LIBUSB_INCLUDE_DIR"] = inc
        except Exception:
            pass
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Smoke-test the installed CLI: st-info --version needs no hardware.
        self.run("st-info --version", env="conanrun")
