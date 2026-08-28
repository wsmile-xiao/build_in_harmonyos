#!/usr/bin/env python3
"""Conan recipe for recastnavigation 1.6.0 — Recast/Detour navigation mesh library."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class RecastnavigationConan(ConanFile):
    name = "recastnavigation"
    version = "1.6.0"
    description = "State-of-the-art navigation-mesh toolset for games (Recast/Detour)"
    license = "Zlib"
    homepage = "https://github.com/recastnavigation/recastnavigation"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

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
        # Upstream requires CMake >= 3.1, but modern CMake removed <3.5 compatibility.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Static by default; build only the core libraries (no demo / examples / tests)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["RECASTNAVIGATION_DEMO"] = "OFF"
        tc.variables["RECASTNAVIGATION_EXAMPLES"] = "OFF"
        tc.variables["RECASTNAVIGATION_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream requires CMake >= 3.1; CMake 4.x removed <3.5 compatibility and
        # only honors the version minimum on the configure command line.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "recastnavigation")
        self.cpp_info.set_property("cmake_target_name", "RecastNavigation::Recast")
        self.cpp_info.components["Recast"].set_property(
            "cmake_target_name", "RecastNavigation::Recast")
        self.cpp_info.components["Recast"].libs = ["Recast"]
        self.cpp_info.components["Detour"].set_property(
            "cmake_target_name", "RecastNavigation::Detour")
        self.cpp_info.components["Detour"].libs = ["Detour"]
        self.cpp_info.components["DetourCrowd"].set_property(
            "cmake_target_name", "RecastNavigation::DetourCrowd")
        self.cpp_info.components["DetourCrowd"].libs = ["DetourCrowd"]
        self.cpp_info.components["DetourCrowd"].requires = ["Detour"]
        self.cpp_info.components["DetourTileCache"].set_property(
            "cmake_target_name", "RecastNavigation::DetourTileCache")
        self.cpp_info.components["DetourTileCache"].libs = ["DetourTileCache"]
        self.cpp_info.components["DetourTileCache"].requires = ["Detour"]
        self.cpp_info.components["DebugUtils"].set_property(
            "cmake_target_name", "RecastNavigation::DebugUtils")
        self.cpp_info.components["DebugUtils"].libs = ["DebugUtils"]
        self.cpp_info.components["DebugUtils"].requires = [
            "Recast", "Detour", "DetourTileCache"]
