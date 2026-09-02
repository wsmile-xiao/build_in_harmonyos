#!/usr/bin/env python3
"""Conan recipe for mp-units 2.5.0.

mp-units is a C++20 header library. The non-module CMake build installs the
headers and exports INTERFACE targets; it does not produce a library or CLI.
The default configuration uses fmt for hosted formatting and disables the
optional GSL contract backends so the package has one published runtime
dependency in the OHOS graph.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get, rmdir


class MPUnitsConan(ConanFile):
    name = "mp-units"
    version = "2.5.0"
    description = "The quantities and units library for C++"
    homepage = "https://github.com/mpusz/mp-units"
    url = "https://github.com/mpusz/mp-units"
    license = "MIT"
    topics = ("units", "quantities", "dimensions", "dimensional-analysis")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "natural_units": [True, False],
    }
    default_options = {
        "natural_units": True,
    }
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake ships Platform/OHOS.cmake on the OHOS worker. Conan's generic
        # system block may otherwise spell this as HarmonyOS, which leaves
        # CMake platform variables unset.
        if str(self.settings.os) in ("Linux", "OHOS"):
            if str(self.settings.os) == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
                tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"

        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.cache_variables["MP_UNITS_BUILD_CXX_MODULES"] = False
        tc.cache_variables["MP_UNITS_BUILD_INSTALL"] = True
        tc.cache_variables["MP_UNITS_API_STD_FORMAT"] = False
        tc.cache_variables["MP_UNITS_API_NO_CRTP"] = False
        tc.cache_variables["MP_UNITS_API_THROWING_CONSTRAINTS"] = False
        tc.cache_variables["MP_UNITS_API_FREESTANDING"] = False
        tc.cache_variables["MP_UNITS_API_CONTRACTS"] = "NONE"
        tc.cache_variables["MP_UNITS_API_NATURAL_UNITS"] = self.options.natural_units
        tc.generate()
        CMakeDeps(self).generate()

    def requirements(self):
        # Hosted mp-units formatting is implemented through fmt when the
        # standard library does not provide std::format. Keep it explicit and
        # transitive because public mp-units headers include fmt headers.
        self.requires("fmt/12.2.0", transitive_headers=True)

    def package_id(self):
        # The package installs headers and INTERFACE targets only; no binary
        # artifact varies with the host settings.
        self.info.clear()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Configure src/ directly: this builds the installable header targets
        # without enabling the upstream Catch2 test tree or examples.
        cmake.configure(build_script_folder="src")
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # The source CMake export encodes options selected at package build
        # time. CMakeDeps is the stable Conan consumer entry point here.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = ["include"]
        # Keep the consumer configuration in sync with the CMake options used
        # to build the installed headers. OHOS libc++ exposes <format> without
        # implementing the complete std::format API, so the explicit fmt
        # backend selection is required for consumers.
        self.cpp_info.defines = [
            "MP_UNITS_API_CONTRACTS=0",
            "MP_UNITS_API_NO_CRTP=0",
            "MP_UNITS_API_NATURAL_UNITS=" + str(int(self.options.natural_units == True)),
            "MP_UNITS_HOSTED=1",
            "MP_UNITS_API_STD_FORMAT=0",
            "MP_UNITS_API_THROWING_CONSTRAINTS=0",
        ]
        self.cpp_info.requires = ["fmt::fmt"]
        self.cpp_info.set_property("cmake_file_name", "mp-units")
        self.cpp_info.set_property("cmake_target_name", "mp-units::mp-units")
        self.cpp_info.set_property("pkg_config_name", "mp-units")
