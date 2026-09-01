#!/usr/bin/env python3
"""Conan recipe — glm 0.9.9.8

GLM (OpenGL Mathematics) — header-only C++ math library, API compatible with GLSL.
Build system: CMake (header-only INTERFACE library, no build artifacts).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GlmConan(ConanFile):
    name = "glm"
    version = "0.9.9.8"
    description = "OpenGL Mathematics — header-only C++ math library, API compatible with GLSL"
    license = "MIT"
    homepage = "https://github.com/g-truc/glm"
    url = ""  # CI fills this

    package_type = "header-library"

    # R32: settings.os check must include both Linux and OHOS
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: apply patches only, no compilation needed
        apply_conandata_patches(self)

    def package(self):
        # Copy the glm/ headers directory (contains glm.hpp and subdirs)
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "glm"),
             dst=os.path.join(self.package_folder, "include", "glm"))
        copy(self, "*.inl", src=os.path.join(self.source_folder, "glm"),
             dst=os.path.join(self.package_folder, "include", "glm"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "glm"),
             dst=os.path.join(self.package_folder, "include", "glm"))
        # Copy license
        copy(self, "copying.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "glm")
        self.cpp_info.set_property("cmake_target_name", "glm::glm")
        # Header-only: no libs to link
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
