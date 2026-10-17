#!/usr/bin/env python3
"""Conan recipe for ctrl-c 1.0.0.

ctrl-c: cross-platform (Windows/Linux/macOS) C++11 helpers that register
callback functions for the Ctrl+C / SIGINT event. Upstream ships two source
files (src/ctrl-c.cpp, src/ctrl-c.h) plus an interactive example under test/
and has no build system of its own (README: "copy source files to your
project"), so the recipe exports the CMake wrapper CMakeLists.txt from the
package directory and configures it with build_script_folder.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class CtrlcConan(ConanFile):
    name = "ctrl-c"
    version = "1.0.0"
    description = "Crossplatform C++11 code to handle the Ctrl+C/SIGINT event in custom functions"
    license = "MIT"
    homepage = "https://github.com/evgenykislov/ctrl-c"
    url = ""  # CI fills this
    topics = ("signal", "ctrl-c", "sigint", "handler")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        # No src_folder: upstream's own sources live in a `src/` subdirectory,
        # and the exported CMakeLists.txt is configured from the same base
        # folder, so `${CMAKE_CURRENT_SOURCE_DIR}/src/ctrl-c.cpp` resolves.
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.export_sources_folder)
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ctrl-c"]
        self.cpp_info.set_property("cmake_file_name", "ctrl-c")
        self.cpp_info.set_property("cmake_target_name", "ctrl-c::ctrl-c")
