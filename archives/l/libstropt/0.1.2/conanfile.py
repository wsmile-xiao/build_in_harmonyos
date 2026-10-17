#!/usr/bin/env python3
"""Conan recipe — libstropt 0.1.2 (CMake)"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibstroptConan(ConanFile):
    name = "libstropt"
    version = "0.1.2"
    description = "Parse option strings with quoting, arguments, escaping, and custom separators"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rd235/libstropt"
    url = "https://github.com/rd235/libstropt"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libstropt supports Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # HarmonyOS is unknown to upstream CMake 4.1, so the platform
            # module does not provide a SONAME linker flag.  Keep one real
            # .so file (HMDFS-safe) while giving it a relocatable SONAME.
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
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
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["stropt"]
        self.cpp_info.set_property("cmake_file_name", "stropt")
        self.cpp_info.set_property("cmake_target_name", "stropt::stropt")
        self.cpp_info.set_property("pkg_config_name", "stropt")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
