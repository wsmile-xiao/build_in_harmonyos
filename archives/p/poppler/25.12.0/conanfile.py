#!/usr/bin/env python3
"""Conan recipe — poppler 25.12.0 (CMake).

PDF rendering library providing PDF document processing functionality.
Patches: 37 patches fixing C++23 std::ranges compatibility (adding std:: prefix)
Dependencies: freetype, fontconfig bypassed via FONT_CONFIGURATION=generic
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PopplerConan(ConanFile):
    name = "poppler"
    version = "25.12.0"
    description = "PDF rendering library providing PDF document processing functionality"
    license = "GPL-2.0-or-later"
    homepage = "https://poppler.freedesktop.org/"

    settings = "os", "compiler", "build_type", "arch"

    # Package options
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Poppler is NOT a system same-name library, so R26 does not apply.
        # Default to shared libraries (controlled by options.shared).
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Font configuration: use generic (no fontconfig dependency on OHOS)
        tc.variables["FONT_CONFIGURATION"] = "generic"
        # Disable optional dependencies not available on OHOS
        tc.variables["ENABLE_BOOST"] = "OFF"
        tc.variables["ENABLE_CPP"] = "ON"
        tc.variables["ENABLE_GLIB"] = "OFF"
        tc.variables["ENABLE_GOBJECT_INTROSPECTION"] = "OFF"
        tc.variables["ENABLE_GTK_DOC"] = "OFF"
        tc.variables["ENABLE_QT5"] = "OFF"
        tc.variables["ENABLE_QT6"] = "OFF"
        tc.variables["ENABLE_UNSTABLE_API_ABI_HEADERS"] = "ON"
        tc.variables["ENABLE_NSS3"] = "OFF"
        tc.variables["ENABLE_GPGME"] = "OFF"
        tc.variables["ENABLE_LIBCURL"] = "OFF"
        tc.variables["ENABLE_LIBTIFF"] = "OFF"
        tc.variables["ENABLE_DCTDECODER"] = "none"
        tc.variables["ENABLE_LIBOPENJPEG"] = "none"
        tc.variables["ENABLE_LCMS"] = "OFF"
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
        self.cpp_info.libs = ["poppler", "poppler-cpp"]
        self.cpp_info.bindirs = ["bin"]
