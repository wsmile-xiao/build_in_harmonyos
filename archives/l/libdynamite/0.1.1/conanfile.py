#!/usr/bin/env python3
"""Conan recipe for libdynamite 0.1.1 — PKWARE explode decompressor.

Tiny C99 library that decompresses PKWARE DCL "implode"/"explode"
streams (used by old installers and some game data files): the public
API is a single streaming entry point,

    DynamiteResult dynamite_explode(dynamite_reader, dynamite_writer,
                                    void *cookie);

with reader/writer callbacks sharing one opaque cookie.  Zero external
dependencies.

Source pinning: upstream has no tags or releases; version 0.1.1 is the
official tree state at commit ccf573ad71cebbfe72f9fe2bead6b2954bb161c0
(2008-05-06 "Upped the version number", whose VERSION file reads 0.1.1),
pinned by sha256.

Build description: upstream ships only `configure.ac.in` and a
`bootstrap` script that needs automake plus libtoolize, neither of which
exists on this platform.  Rather than checking in the generated
autotools output (tens of thousands of lines for three C files, which
also pushed the change past the review tooling's size limit), the recipe
carries a small CMakeLists.txt that builds the same artifacts from the
unmodified upstream sources.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class LibdynamiteConan(ConanFile):
    name = "libdynamite"
    version = "0.1.1"
    description = ("libdynamite - decompressor for PKWARE DCL implode/"
                   "explode compressed data")
    license = "MIT"
    homepage = "https://github.com/twogood/dynamite"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        copy(self, "CMakeLists.txt", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdynamite is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]).
        # CMakeLists.txt travels with the recipe (export_sources) and lands
        # in this same folder, so there is nothing to copy here.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF")
        toolchain.generate()

    def build(self):
        # Explicitly neutralize LD_LIBRARY_PATH: some CI workers carry an
        # ambient LD pointing at /usr/local/lib whose incompatible
        # libxml2.so.16 breaks the SDK's lld on every link (CI-021 build
        # #48068 — mechanism documented in libodfgen/libabw).
        shield = Environment()
        shield.define("LD_LIBRARY_PATH", "")
        with shield.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdynamite")
        self.cpp_info.set_property("cmake_target_name",
                                   "libdynamite::libdynamite")
        self.cpp_info.set_property("pkg_config_name", "libdynamite")
        self.cpp_info.libs = ["dynamite"]
