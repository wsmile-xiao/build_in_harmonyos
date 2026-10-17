#!/usr/bin/env python3
"""Conan recipe for lci 1.3 — justinmeza/lci, a LOLCODE 1.3 interpreter in C.

Build: CMake (single `lci` executable). Upstream CMakeLists requires
CMake >= 3.31; builds with the repo OHOS aarch64 profile and installs
the interpreter to bin/. R38: lci is a CLI tool, declared in the
software-level commands.json.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LciConan(ConanFile):
    name = "lci"
    version = "1.3"
    description = "lci — a lightweight interpreter for the LOLCODE 1.3 programming language"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/justinmeza/lci"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lci supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if os.path.isfile(os.path.join(self.source_folder, "COPYING")):
            copy(self, "COPYING", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

    def package_info(self):
        # lci is an application (interpreter binary), not a library.
        self.cpp_info.bindirs = ["bin"]
