#!/usr/bin/env python3
"""Conan recipe for clip 0.7 — C++ image processing library & CLI tool.

clip is a command-line image processing tool for cropping and resizing images.
It depends on cairo, freetype, harfbuzz, fontconfig, libpng, and fribidi.
Since fmt is not available on the ohpcd conan remote, it is vendored from source.

R26: BUILD_SHARED_LIBS controlled by Conan options.
R32: settings.os supports both Linux and OHOS.
R33: No hardcoded compiler paths — uses ConanToolchain.
R38: Produces both library (libclip) and executable (clip CLI).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ClipConan(ConanFile):
    name = "clip"
    version = "0.7"
    description = "Command-line image processing tool for cropping and resizing images"
    license = "MIT"
    homepage = "https://github.com/asmuth/clip"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("cairo/1.18.4")
        self.requires("freetype/2.14.3")
        self.requires("harfbuzz/14.2.0.1")
        self.requires("fontconfig/2.18.1")
        self.requires("libpng/1.6.58")
        self.requires("fribidi/1.0.16")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Extract clip source
        get(self, **self.conan_data["sources"], strip_root=True)
        # Extract vendored fmt source into third_party/fmt
        fmt_data = self.conan_data["fmt_source"]
        get(self, **fmt_data, strip_root=True,
            destination=os.path.join(self.source_folder, "third_party/fmt"))

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # R26: Control shared/static via Conan option
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
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
        # clip static lib + vendored fmt static lib
        self.cpp_info.libs = ["clip", "fmt"]
