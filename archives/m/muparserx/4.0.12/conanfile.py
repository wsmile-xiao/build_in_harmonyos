#!/usr/bin/env python3
"""Conan recipe for muparserx 4.0.12 — CMake-based math parser library, HarmonyOS PC."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class MuparserxConan(ConanFile):
    name = "muparserx"
    version = "4.0.12"
    description = "muparserX - a mathematical expression parser library (extension of muparser)"
    license = "BSD-2-Clause"
    homepage = "https://beltoforion.de/en/muparserx/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Upstream CMakeLists declares cmake_minimum_required 2.8.12; modern CMake
        # (>=3.5) rejects it without this policy override.
        toolchain.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_EXAMPLES"] = False
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        toolchain.variables["CMAKE_CXX_STANDARD"] = 17
        toolchain.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream CMakeLists requires CMake < 3.5 policy; modern CMake rejects
        # it, so force the policy minimum on the configure command line too.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream installs headers under include/muparserx/ (see CMakeLists.txt)
        self.cpp_info.includedirs = ["include/muparserx"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["muparserx"]
        self.cpp_info.set_property("cmake_file_name", "muparserx")
        self.cpp_info.set_property("cmake_target_name", "muparserx::muparserx")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
