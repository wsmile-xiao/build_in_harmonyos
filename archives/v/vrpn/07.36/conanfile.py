#!/usr/bin/env python3
"""Conan recipe for vrpn 07.36 - OHOS aarch64 adaptation.

Patch 0001: CMake native detection on HarmonyOS yields CMAKE_SYSTEM_NAME=HarmonyOS
(no Platform module exists for that name), so the UNIX variable stays FALSE.
Upstream gates the atmellib subdirectory behind if(UNIX) while server code
references vrpn_atmel behind if(NOT WIN32); the mismatch broke the vrpn_server
link with "unable to find library -lvrpn_atmel". Gate aligned to NOT WIN32.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VrpnConan(ConanFile):
    name = "vrpn"
    version = "07.36"
    description = "VRPN (Virtual-Reality Peripheral Network) device access library and server tools"
    license = "MIT"
    homepage = "https://github.com/vrpn/vrpn"
    url = "https://github.com/vrpn/vrpn"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream demo/test executables are gated by BUILD_TESTING; package-level
        # L1 testing is done by test_package. Client/server libs and tools stay ON.
        tc.variables["BUILD_TESTING"] = "OFF"
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
        self.cpp_info.libs = [
            "vrpn", "vrpnserver", "quat", "gpsnmea", "vrpn_atmel", "vrpn_timecode_generator",
        ]
