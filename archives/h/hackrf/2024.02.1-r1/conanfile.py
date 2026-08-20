#!/usr/bin/env python3
"""Conan recipe — hackrf 2024.02.1-r1 (CMake project).

Host software for HackRF Software Defined Radio peripheral.
Includes libhackrf library and hackrf-tools command-line utilities.

Source: https://github.com/greatscottgadgets/hackrf
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HackrfConan(ConanFile):
    name = "hackrf"
    version = "2024.02.1-r1"
    description = "Host software for HackRF Software Defined Radio (libhackrf + tools)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/greatscottgadgets/hackrf"
    url = "https://github.com/greatscottgadgets/hackrf"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS; use Linux for cmake platform detection
        # R32: recipe supports both Linux and OHOS (settings.os in ("Linux", "OHOS"))
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["INSTALL_UDEV_RULES"] = "OFF"
        # Pass libusb paths from Conan dependency to custom FindUSB1.cmake module
        libusb = self.dependencies["libusb"]
        libusb_root = libusb.package_folder
        tc.variables["LIBUSB_INCLUDE_DIR"] = os.path.join(libusb_root, "include", "libusb-1.0")
        tc.variables["LIBUSB_LIBRARIES"] = os.path.join(libusb_root, "lib", "libusb-1.0.so")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="host")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hackrf"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_module_file_name", "LIBHACKRF")
        self.cpp_info.set_property("cmake_file_name", "hackrf")
        self.cpp_info.set_property("pkg_config_name", "libhackrf")
