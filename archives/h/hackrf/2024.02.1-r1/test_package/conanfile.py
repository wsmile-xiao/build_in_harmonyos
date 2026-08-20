#!/usr/bin/env python3
"""Conan test_package — hackrf 2024.02.1-r1.

Consumer-side test: calls hackrf_library_version() and hackrf_init()/hackrf_exit()
to verify the library is properly installed and functional.

Uses direct compilation instead of CMake to ensure static linking against libhackrf.a,
avoiding the HarmonyOS musl dynamic linker issue with loading libhackrf.so.0.
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class HackrfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        hackrf = self.dependencies["hackrf"]
        libusb = self.dependencies["libusb"]
        hackrf_pkg = hackrf.package_folder
        libusb_pkg = libusb.package_folder
        include_dir = os.path.join(hackrf_pkg, "include")
        static_lib = os.path.join(hackrf_pkg, "lib", "libhackrf.a")
        libusb_lib = os.path.join(libusb_pkg, "lib")

        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_hackrf")
        self.run(
            f'clang -o {out} {src} '
            f'-I{include_dir} '
            f'{static_lib} '
            f'-L{libusb_lib} -lusb-1.0 '
            f'-lpthread -lm '
            f'-Wl,-rpath,{libusb_lib} '
            f'-Wl,--disable-new-dtags'
        )

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_hackrf")
        self.run(test_bin)
