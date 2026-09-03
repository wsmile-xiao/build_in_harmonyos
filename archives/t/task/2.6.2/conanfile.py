#!/usr/bin/env python3
"""Conan recipe - task 2.6.2 (Taskwarrior, CMake, command-line task manager).

Dependencies:
  - uuid/2.40.1 (util-linux libuuid, static)

Notes:
  - ENABLE_SYNC=OFF because GnuTLS is not available in the conan registry.
    The full GnuTLS dependency chain (nettle, libtasn1, libgcrypt, etc.)
    is not yet adapted. Sync support requires GnuTLS for TLS connections.
  - libshared submodule is downloaded separately (not in the GitHub tarball).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TaskConan(ConanFile):
    name = "task"
    version = "2.6.2"
    description = "Command-line task manager (Taskwarrior)"
    license = "MIT"
    homepage = "https://taskwarrior.org/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("uuid/2.40.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download main source
        get(self, **self.conan_data["sources"]["task"], strip_root=True)
        # Download libshared submodule (not included in GitHub tarball)
        libshared_dir = os.path.join(self.source_folder, "src", "libshared")
        os.makedirs(libshared_dir, exist_ok=True)
        get(self, **self.conan_data["sources"]["libshared"],
            destination=libshared_dir, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Pass uuid dependency paths to CMake (Taskwarrior uses find_path/find_library, not find_package)
        uuid_dep = self.dependencies["uuid"]
        tc.variables["UUID_INCLUDE_DIR"] = uuid_dep.cpp_info.includedirs[0]
        tc.variables["UUID_LIBRARY"] = os.path.join(
            uuid_dep.cpp_info.libdirs[0], "libuuid.a")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be on cmdline (before toolchain loads)
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "ENABLE_SYNC": "OFF",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove libtool files
        rmdir(self, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
