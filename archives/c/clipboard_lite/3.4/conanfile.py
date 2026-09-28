#!/usr/bin/env python3
"""Conan recipe for clipboard_lite 3.4 — cross-platform clipboard management library.

clipboard_lite is a lightweight C++14 clipboard library (MIT). The Linux/OHOS
backend uses X11 (libx11) plus the Xfixes (libxfixes) and XTest (libxtst)
extensions; protocol/atom headers come from xorgproto.

R26: static linking by default (shared is optional via Conan option).
R32: settings.os covers both Linux and OHOS (same X11 backend branch).
R33: no hardcoded compiler paths — uses ConanToolchain.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ClipboardLiteConan(ConanFile):
    name = "clipboard_lite"
    version = "3.4"
    description = "Cross-platform clipboard management library (lightweight and fast)"
    license = "MIT"
    homepage = "https://github.com/smasherprog/clipboard_lite"
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
        # Linux/OHOS X11 backend: Xlib.h (libx11), Xatom.h (xorgproto),
        # Xfixes.h (libxfixes), XTest.h (libxtst). All published on ohpcd.
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxfixes/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxtst/6.1.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # R26: control static/shared via Conan option
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Upstream CMakeLists uses find_package(X11 REQUIRED) and consumes
        # X11_INCLUDE_DIR / X11_LIBRARIES / X11_Xfixes_LIB / X11_XTest_LIB.
        # Inject the conan dependency package folders so the OHOS build can
        # resolve X11 headers/libs (the registry has no system X11 dev tree).
        inc_dirs = []
        lib_paths = []
        for dep in ("libx11", "xorgproto", "libxfixes", "libxtst"):
            inc_dirs.append(os.path.join(self.dependencies[dep].package_folder, "include"))
            lib_paths.append(os.path.join(self.dependencies[dep].package_folder, "lib"))
        tc.variables["X11_INCLUDE_DIR"] = ";".join(inc_dirs)
        # Upstream Test/CMakeLists.txt links ${X11_LIBRARIES} ${X11_Xfixes_LIB}
        # ${X11_XTest_LIB}; pass the actual .so files (dir paths are ignored by
        # the linker, which caused G2 undefined-symbol failures).
        tc.variables["X11_LIBRARIES"] = os.path.join(
            self.dependencies["libx11"].package_folder, "lib", "libX11.so")
        tc.variables["X11_Xfixes_LIB"] = os.path.join(
            self.dependencies["libxfixes"].package_folder, "lib", "libXfixes.so")
        tc.variables["X11_XTest_LIB"] = os.path.join(
            self.dependencies["libxtst"].package_folder, "lib", "libXtst.so")
        # Let FindX11/find_library resolve any remaining extension libs.
        tc.variables["CMAKE_LIBRARY_PATH"] = os.pathsep.join(lib_paths)
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
        self.cpp_info.libs = ["clipboard_lite"]
        # Consumers of the static lib need the X11 backend symbols at link time.
        self.cpp_info.requires = [
            "libx11::libx11",
            "xorgproto::xorgproto",
            "libxfixes::libxfixes",
            "libxtst::libxtst",
        ]