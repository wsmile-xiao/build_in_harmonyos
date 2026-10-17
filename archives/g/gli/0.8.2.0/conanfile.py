#!/usr/bin/env python3
"""Conan recipe — gli 0.8.2.0

GLI (GPU Image) — header-only C++ image library, API compatible with GLSL.
Build system: CMake (header-only INTERFACE library, no build artifacts).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GliConan(ConanFile):
    name = "gli"
    version = "0.8.2.0"
    description = "GPU Image — header-only C++ image library, API compatible with GLSL"
    license = "MIT"
    homepage = "https://github.com/g-truc/gli"
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
        # Copy the gli/ headers directory (contains gli.hpp and subdirs)
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "gli"),
             dst=os.path.join(self.package_folder, "include", "gli"))
        copy(self, "*.inl", src=os.path.join(self.source_folder, "gli"),
             dst=os.path.join(self.package_folder, "include", "gli"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "gli"),
             dst=os.path.join(self.package_folder, "include", "gli"))
        # gli public headers include <glm/glm.hpp>; upstream bundles GLM 0.9.8 in
        # external/glm. Ship the bundled GLM headers so consumers build out of the box.
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "external", "glm", "glm"),
             dst=os.path.join(self.package_folder, "include", "glm"))
        copy(self, "*.inl", src=os.path.join(self.source_folder, "external", "glm", "glm"),
             dst=os.path.join(self.package_folder, "include", "glm"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "external", "glm", "glm"),
             dst=os.path.join(self.package_folder, "include", "glm"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gli")
        self.cpp_info.set_property("cmake_target_name", "gli::gli")
        # Header-only: no libs to link
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
