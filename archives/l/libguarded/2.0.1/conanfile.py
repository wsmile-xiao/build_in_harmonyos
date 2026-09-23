#!/usr/bin/env python3
"""Conan recipe for CsLibGuarded (libguarded) 2.0.1.

CsLibGuarded is a header-only C++20 library of thread-safe guards for
protecting shared data.  The upstream CMake project is an INTERFACE
library; this recipe keeps the upstream build (including the upstream
Catch2 unit tests) and installs through the upstream CMake install
rules.  The portability patch in patches/ extends the upstream
GNUInstallDirs platform branch with OHOS/HarmonyOS so that
CMAKE_INSTALL_INCLUDEDIR/LIBDIR are defined on this platform; without
it the install destinations degrade to absolute paths such as
/cmake/CsLibGuarded and fail.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibguardedConan(ConanFile):
    name = "libguarded"
    version = "2.0.1"
    description = "Header-only C++20 library of thread-safe guards for protecting shared data"
    license = "BSD-2-Clause"
    homepage = "https://github.com/copperspice/cs_libguarded"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Standard patch export hook; keeps future patches safe and is
        # required by the repository verifier even in the no-patch case.
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Keep the real platform identity: the OHOS-adapted Conan toolchain
        # maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, and the portability
        # patch teaches the upstream GNUInstallDirs branch to accept both
        # the OHOS and HarmonyOS spellings.  No Linux override is used.
        tc.cache_variables["BUILD_TESTS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Runs the upstream Catch2 suite (21 ctest cases) on the device.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_id(self):
        # The package contains headers and CMake interface metadata only.
        self.info.clear()

    def package_info(self):
        # Upstream installs headers to <prefix>/include/CsLibGuarded/ and
        # exposes both include roots through the installed interface target.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include", "include/CsLibGuarded"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "CsLibGuarded")
        self.cpp_info.set_property("cmake_target_name", "CsLibGuarded::CsLibGuarded")
