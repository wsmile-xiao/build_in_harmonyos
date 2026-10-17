#!/usr/bin/env python3
"""Conan recipe for enkits 1.12 (CMake).

enkiTS is a C and C++ task scheduler for creating parallel programs.
It is a header + static library (libenkiTS.a) with no external dependencies
beyond the system pthreads library. The CMake build is driven with the
upstream options: ENKITS_INSTALL=ON (install the library + headers),
ENKITS_BUILD_EXAMPLES=OFF (skip the example/test executables) and
ENKITS_BUILD_SHARED=OFF (static archive, R26-compatible).

Platform note (aarch64/OHOS): enkiTS v1.12 already ships the
`#include <initializer_list>` guard in src/TaskScheduler.h that earlier
xmake-repo patches had to add manually, so no source patch is required.
"""
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EnkitsConan(ConanFile):
    name = "enkits"
    version = "1.12"
    description = "A C and C++ task scheduler for creating parallel programs"
    license = "Zlib"
    homepage = "https://github.com/dougbinks/enkiTS"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: all build configuration is passed via CMakeToolchain variables,
        # not via shell environment variables.
        tc = CMakeToolchain(self)
        # R26: static archive by default to avoid polluting /lib or /lib64
        # with a same-named shared object.
        tc.variables["ENKITS_INSTALL"] = "ON"
        tc.variables["ENKITS_BUILD_EXAMPLES"] = "OFF"
        tc.variables["ENKITS_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENKITS_BUILD_C_INTERFACE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove CMake config files shipped by the install target; Conan
        # generates its own CMakeDeps integration.
        rmdir(self, Path(self.package_folder) / "lib" / "cmake")

    def package_info(self):
        # The upstream CMake target is "enkiTS" (libenkiTS.a / -lenkiTS).
        self.cpp_info.libs = ["enkiTS"]
        self.cpp_info.set_property("cmake_file_name", "enkiTS")
        self.cpp_info.set_property("cmake_target_name", "enkiTS::enkiTS")
        self.cpp_info.set_property("pkg_config_name", "enkiTS")
        # enkiTS uses std::thread / std::mutex (C++11); on OHOS/Linux-clang
        # the C++ runtime (libc++) and pthreads must be linked.
        if self.settings.os in ("Linux", "OHOS"):  # R32
            self.cpp_info.system_libs = ["pthread"]
