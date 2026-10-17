#!/usr/bin/env python3
"""Conan recipe - libuinputplus 0.1.4 (CMake).

libuInputPlus is an easy-to-use C++ library for the Linux kernel uinput
interface, used to create virtual input devices from userspace.
Build system: CMake.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibuinputplusConan(ConanFile):
    name = "libuinputplus"
    version = "0.1.4"
    description = "Easy-to-use C++ library for the Linux uinput interface (virtual input devices)"
    license = "MIT"
    homepage = "https://github.com/YukiWorkshop/libuInputPlus"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 3.0); CMake >= 4
        # refuses to configure projects requiring < 3.5 (knowledge E103).
        # Lift the policy floor via cache variable instead of patching upstream.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = ["uInputPlus"]
        # Upstream (v0.1.4 tag) installs headers into include/uInputPlus/ and
        # its uInputPlus.pc points Cflags into that subdir, so consumers use a
        # flat #include "uInput.hpp" (matches libevdev-style subdir layouts).
        self.cpp_info.includedirs = ["include/uInputPlus"]
        self.cpp_info.set_property("cmake_file_name", "uInputPlus")
        self.cpp_info.set_property("cmake_target_name", "uInputPlus::uInputPlus")
        self.cpp_info.set_property("pkg_config_name", "uInputPlus")
