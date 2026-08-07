#!/usr/bin/env python3
"""Conan recipe for hidapi 0.14.0 — HID device access library (libusb backend).

hidapi provides a C library for communicating with USB and Bluetooth HID devices.
This recipe builds the libusb-based implementation, suitable for HarmonyOS.
"""
from conan import ConanFile
from conan.tools.files import get, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
import os


class HidapiConan(ConanFile):
    name = "hidapi"
    version = "0.14.0"
    description = "A Simple library for communicating with USB and Bluetooth HID devices"
    license = "BSD-3-Clause OR GPL-3.0-only"
    homepage = "https://github.com/libusb/hidapi"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be a cache variable (command-line -D)
        # because it's needed before the toolchain file is loaded (at cmake_minimum_required time)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["HIDAPI_NO_ICONV"] = "ON"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # Patch libusb/CMakeLists.txt to support Conan CMakeDeps target
        cmake_file = os.path.join(self.source_folder, "libusb", "CMakeLists.txt")
        replace_in_file(
            self,
            cmake_file,
            "if(TARGET usb-1.0)\n    target_link_libraries(hidapi_libusb PRIVATE usb-1.0)",
            "find_package(libusb-1.0 QUIET)\n"
            "if(TARGET libusb-1.0::libusb-1.0)\n"
            "    target_link_libraries(hidapi_libusb PRIVATE libusb-1.0::libusb-1.0)\n"
            "elseif(TARGET usb-1.0)\n"
            "    target_link_libraries(hidapi_libusb PRIVATE usb-1.0)",
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hidapi-libusb"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "hidapi")
        self.cpp_info.set_property("cmake_target_name", "hidapi::hidapi")
        self.cpp_info.set_property("pkg_config_name", "hidapi-libusb")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
