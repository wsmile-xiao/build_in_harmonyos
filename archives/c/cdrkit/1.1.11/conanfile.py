#!/usr/bin/env python3
"""Conan recipe for cdrkit 1.1.11 — CD/DVD recording and imaging tools.

Adapted for OpenHarmony / HarmonyOS PC (aarch64).
Key adaptations:
  - cmake_minimum_required(VERSION 3.5) for CMake 4.x compatibility
  - HAVE_RCMD disabled (rcmd() not in OHOS bionic libc; uses _rcmdrsh fallback)
  - HAVE_SETREUID/HAVE_SETREGID disabled (unimplemented syscalls on OHOS; uses seteuid/setegid)
  - libcap API replaced with kernel capget/capset API
  - pthread_cancel replaced with graceful thread shutdown
  - __THROW fallback for bionic libc
  - extern outfile declaration to fix lld duplicate symbol
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CdrkitConan(ConanFile):
    name = "cdrkit"
    version = "1.1.11"
    description = "CD/DVD recording and imaging tools (wodim, genisoimage, icedax)"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/cdrkit/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bzip2/1.0.8")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_CROSSCOMPILING"] = "OFF"

        # Propagate bzip2 and zlib include/lib paths to CMake
        # cdrkit's CMakeLists.txt links bz2 and z directly (not via find_package)
        cflags = []
        ldflags = []
        for dep_name in ["bzip2", "zlib"]:
            dep = self.dependencies.get(dep_name)
            if dep:
                inc = dep.cpp_info.includedirs[0] if dep.cpp_info.includedirs else ""
                lib = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else ""
                if inc:
                    cflags.append(f"-I{inc}")
                if lib:
                    ldflags.append(f"-L{lib}")

        existing_cflags = tc.variables.get("CMAKE_C_FLAGS", "")
        tc.variables["CMAKE_C_FLAGS"] = f"{existing_cflags} {' '.join(cflags)}".strip()

        existing_ldflags = tc.variables.get("CMAKE_EXE_LINKER_FLAGS", "")
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = f"{existing_ldflags} {' '.join(ldflags)}".strip()

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
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
