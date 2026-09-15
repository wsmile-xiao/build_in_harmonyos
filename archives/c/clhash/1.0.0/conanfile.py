#!/usr/bin/env python3
"""Conan recipe for clhash 1.0.0, a C library with C++ wrappers."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ClhashConan(ConanFile):
    name = "clhash"
    version = "1.0.0"
    description = "Fast 64-bit universal hashing via carry-less multiplication"
    license = "Apache-2.0"
    homepage = "https://github.com/simdhash/clhash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"clhash supports Linux/OHOS only, got {self.settings.os}"
            )

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
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CLHASH_INSTALL"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream CTest suite: clhash_unit and clhash_cppunit.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.libs = ["clhash"]
        self.cpp_info.set_property("cmake_file_name", "clhash")
        self.cpp_info.set_property("cmake_target_name", "clhash::clhash")
