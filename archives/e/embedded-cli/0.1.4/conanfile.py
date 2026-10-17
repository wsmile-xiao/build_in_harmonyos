#!/usr/bin/env python3
"""Conan recipe — embedded-cli 0.1.4 (CMake, static library).

Single-header CLI library intended for use in embedded systems.
Builds static lib from lib/src/embedded_cli.c, public header lib/include/embedded_cli.h.
Upstream has no install() rules, so package() copies header + archive manually.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class EmbeddedCliConan(ConanFile):
    name = "embedded-cli"
    version = "0.1.4"
    description = "Single-header CLI library intended for use in embedded systems."
    license = "MIT"
    homepage = "https://github.com/funbiscuit/embedded-cli"
    url = "https://github.com/funbiscuit/embedded-cli"

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
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_SINGLE_HEADER"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "embedded_cli.h",
             src=os.path.join(self.source_folder, "lib", "include"),
             dst=os.path.join(self.package_folder, "include"))
        # Upstream targets the static lib in the lib/ subdirectory of the CMake
        # binary dir (add_subdirectory(lib)); copy it into the package lib/ dir.
        lib_dir = os.path.join(self.build_folder, "lib")
        archive = os.path.join(lib_dir, "libembedded_cli_lib.a")
        if not os.path.exists(archive):
            # fallback: search for the archive anywhere under the build folder
            candidates = [
                os.path.join(root, name)
                for root, _dirs, files in os.walk(self.build_folder)
                for name in files if name == "libembedded_cli_lib.a"
            ]
            if candidates:
                archive = candidates[0]
        copy(self, os.path.basename(archive),
             src=os.path.dirname(archive),
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["embedded_cli_lib"]
        self.cpp_info.set_property("cmake_file_name", "embedded-cli")
        self.cpp_info.set_property("cmake_target_name", "embedded-cli::embedded-cli")
