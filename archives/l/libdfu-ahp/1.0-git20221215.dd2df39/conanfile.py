#!/usr/bin/env python3
"""Conan recipe for the locked libdfu-ahp 2022 snapshot."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibdfuAhpConan(ConanFile):
    name = "libdfu-ahp"
    version = "1.0-git20221215.dd2df39"
    description = "C library for programming USB DFU-capable devices"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ahp-electronics/libdfu"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

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
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        if str(self.settings.os) == "OHOS":
            # CMake has no HarmonyOS platform module; retain an ELF SONAME so
            # consumers do not record this machine's Conan cache path.
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
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
        self.cpp_info.libs = ["dfu"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libdfu")
        self.cpp_info.set_property("cmake_target_name", "libdfu::libdfu")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
