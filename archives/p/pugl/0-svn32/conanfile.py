#!/usr/bin/env python3
"""Conan recipe — Pugl 0-svn32 (CMake HarmonyOS backend)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PuglConan(ConanFile):
    name = "pugl"
    version = "0-svn32"
    description = "Minimal portable OpenGL GUI API with a HarmonyOS EGL backend"
    license = "ISC"
    homepage = "https://drobilla.net/software/pugl.html"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "This Pugl backend targets HarmonyOS/OpenHarmony"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = ["include/pugl-0"]
        self.cpp_info.libs = ["pugl-0"]
        self.cpp_info.defines = ["PUGL_GLES_BACKEND"]
        self.cpp_info.system_libs = ["EGL", "GLESv3", "native_window"]
        self.cpp_info.set_property("cmake_file_name", "pugl")
        self.cpp_info.set_property("cmake_target_name", "pugl::pugl")
        self.cpp_info.set_property("pkg_config_name", "pugl-0")
