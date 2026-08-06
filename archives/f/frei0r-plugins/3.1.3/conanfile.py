#!/usr/bin/env python3
"""Conan recipe for frei0r-plugins 3.1.3 — a minimalistic plugin API for video effects.

frei0r-plugins builds .so MODULE plugins (runtime-loaded, not link-time libraries).
The package provides:
  - Headers (frei0r.h, frei0r.hpp, frei0r/*.h) defining the plugin API
  - .so plugin files in lib/frei0r-1/ loaded at runtime via dlopen
  - frei0r.pc pkg-config file (Libs: empty, Cflags: -I${includedir})
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, unzip, check_sha256
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Frei0rPluginsConan(ConanFile):
    name = "frei0r-plugins"
    version = "3.1.3"
    description = "A minimalistic plugin API for video effects"
    license = "MIT"
    homepage = "https://github.com/dyne/frei0r"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("cairo/1.18.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Support local source tarball for environments without GitHub access.
        # CI has direct GitHub access and will use the normal download path.
        local_tarball = os.path.join(
            os.path.expanduser("~"), "tmp", "builds",
            "frei0r-plugins-3.1.3.tar.gz"
        )
        if os.path.isfile(local_tarball):
            check_sha256(self, local_tarball, self.conan_data["sources"]["sha256"])
            unzip(self, local_tarball, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # cmake 4.1.2 on OHOS requires CMAKE_SYSTEM_NAME=Linux for try_compile checks
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Set project version to match package version (CMakeLists.txt defaults to 3.0.0)
        tc.variables["FREI0R_VERSION"] = "3.1.3"
        # Disable optional dependencies not available as precompiled packages
        tc.variables["WITHOUT_OPENCV"] = "ON"
        tc.variables["WITHOUT_GAVL"] = "ON"
        tc.variables["NO_SSE2"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # frei0r-plugins provides runtime-loaded .so modules, not link-time libraries.
        # Applications include frei0r.h and load plugins via dlopen from lib/frei0r-1/.
        self.cpp_info.set_property("cmake_file_name", "frei0r")
        self.cpp_info.set_property("cmake_target_name", "frei0r::frei0r")
        self.cpp_info.set_property("pkg_config_name", "frei0r")
        self.cpp_info.libdirs = ["lib/frei0r-1"]
        self.cpp_info.includedirs = ["include"]
