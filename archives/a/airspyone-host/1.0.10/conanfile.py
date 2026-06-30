#!/usr/bin/env python3
"""Conan recipe — airspyone-host 1.0.10 (CMake project).

AirSpy user-mode driver and associated tools for Software Defined Radio.
Source: https://github.com/airspy/airspyone_host
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AirspyonehostConan(ConanFile):
    name = "airspyone-host"
    version = "1.0.10"
    description = "AirSpy user-mode driver and associated tools"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/airspy/airspyone_host"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libusb is installed as a system library (cmd-pkgs prebuilt)
        # No Conan package available, declare as system dependency
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x compatibility: project uses cmake_minimum_required(2.8)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS, use Linux for compatibility
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # R32: support both Linux and OHOS
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["airspy"]
        # System dependencies: libusb-1.0 (installed via cmd-pkgs)
        self.cpp_info.system_libs = ["usb-1.0"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_module_file_name", "LIBAIRSPY")
        self.cpp_info.set_property("cmake_file_name", "airspy")
        self.cpp_info.set_property("pkg_config_name", "libairspy")
