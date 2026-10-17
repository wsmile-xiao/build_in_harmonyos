#!/usr/bin/env python3
"""Conan recipe for kodi-platform 20250416 — Kodi PVR add-on platform support library.

Upstream: https://github.com/xbmc/kodi-platform (tag kodiplatform-20250416).

kodi-platform provides the XML helper utilities (XMLUtils) used by Kodi PVR
add-ons. It is a thin abstraction layer that only links against tinyxml and
p8-platform; it does NOT require the full Kodi application.

The upstream CMakeLists.txt resolves its dependencies through modules shipped
inside the kodi-addon-dev package (FindKodi.cmake + in-tree FindTinyXML.cmake),
which expects a system-wide Kodi SDK installation. The ohpcd registry has no
kodi package; since the single translation unit (src/util/XMLUtils.cpp) uses
nothing from the Kodi headers, this recipe supplies a minimal CMakeLists.txt
(under recipe-cmake/, consumed via build_script_folder) that builds the same
sources against tinyxml and p8-platform through Conan's CMakeDeps targets.
Upstream sources are built unmodified.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class KodiPlatformConan(ConanFile):
    name = "kodi-platform"
    version = "20250416"
    description = "Platform support library for Kodi add-ons (XML utilities)"
    license = "GPL-2.0"
    homepage = "https://github.com/xbmc/kodi-platform"
    url = "https://github.com/xbmc/kodi-platform"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    generators = "CMakeDeps"
    exports_sources = "recipe-cmake/*"

    def requirements(self):
        # W0 checked (conan download --only-recipe against the ohpcd remote):
        # both dependencies are published on the registry
        self.requires("tinyxml/2.6.2")
        self.requires("p8-platform/2.1.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The upstream tarball ships its own CMakeLists.txt whose
        # find_package(Kodi REQUIRED) needs the kodi-addon-dev SDK (not
        # available on the ohpcd registry). exports_sources are merged into
        # the source folder BEFORE source() runs, so the tarball extraction
        # would clobber same-named files. Ship our build entry points in a
        # "recipe-cmake/" subfolder (which the tarball does not contain)
        # and copy them out to a build-only subfolder after extraction.
        copy(self, "*", src=os.path.join(self.recipe_folder, "recipe-cmake"),
             dst=os.path.join(self.source_folder, "recipe-cmake"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # E092: CMake has no HarmonyOS platform module, use Linux
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="recipe-cmake")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["kodiplatform"]
        self.cpp_info.set_property("cmake_file_name", "kodiplatform")
        self.cpp_info.set_property("cmake_target_name", "kodiplatform::kodiplatform")
        self.cpp_info.set_property("pkg_config_name", "kodiplatform")
        self.cpp_info.requires = ["tinyxml::tinyxml", "p8-platform::p8-platform"]
