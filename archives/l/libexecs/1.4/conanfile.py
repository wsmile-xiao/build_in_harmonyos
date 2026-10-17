#!/usr/bin/env python3
"""Conan recipe — libexecs (s2argv-execs) 1.4."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.build import cross_building


class LibexecsConan(ConanFile):
    name = "libexecs"
    version = "1.4"
    description = "execs — execute a file taking its arguments from a string (libexecs)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/virtualsquare/s2argv-execs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libexecs requires a POSIX C target")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Shared libs: libexecs.so / libexecs-embedded.so
        # Static libs: libexecs.a   / libexecs-embedded.a (OUTPUT_NAME execs)
        libs = ["execs-embedded", "execs"]
        self.cpp_info.set_property("cmake_file_name", "execs")
        self.cpp_info.set_property("cmake_target_name", "execs::execs")
        if self.options.shared:
            self.cpp_info.libs = ["execs-embedded", "execs"]
        else:
            self.cpp_info.libs = ["execs-embedded", "execs"]
        self.cpp_info.system_libs = ["c"]
