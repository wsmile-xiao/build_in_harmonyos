#!/usr/bin/env python3
"""Conan recipe — guilite 2.1 (CMake static library).

GuiLite is a lightweight C++ UI framework. Upstream provides a
CMakeLists.txt that builds a STATIC library `GuiLite` from
core/ + core/adapter/api_linux.cpp + widgets/ sources with -DGUILITE_ON.
Headers live in core_include/ and widgets_include/ (included as
"core_include/api.h", "widgets_include/button.h", ...).
Upstream CMake has no install() rule and runs a telemetry script
(.sync.sh -> PowerBI) at configure time; the packaged recipe patches
that out and installs headers + archive manually.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class GuiliteConan(ConanFile):
    name = "guilite"
    version = "2.1"
    description = "GuiLite - a lightweight C++ UI framework"
    license = "MIT"
    homepage = "https://github.com/idea4good/GuiLite"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GuiLite v2.1 tag tarball nests all sources under workspace/.
        # Lift them to the source root so the root CMakeLists.txt is found.
        workspace = os.path.join(self.source_folder, "workspace")
        if os.path.isdir(workspace):
            for entry in sorted(os.listdir(workspace)):
                os.rename(os.path.join(workspace, entry),
                          os.path.join(self.source_folder, entry))
            os.rmdir(workspace)

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
        # Upstream CMakeLists has no install() rule; install headers + lib manually.
        copy(self, "core_include/*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "widgets_include/*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        lib_ext = ".so" if self.options.shared else ".a"
        copy(self, f"libGuiLite{lib_ext}", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["GuiLite"]
