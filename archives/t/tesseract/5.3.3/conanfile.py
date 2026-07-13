#!/usr/bin/env python3
"""Conan recipe for tesseract 5.3.3 (CMake build system).

Build system: CMake
Dependencies: leptonica/1.87.0
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class TesseractConan(ConanFile):
    name = "tesseract"
    version = "5.3.3"
    description = "Tesseract Open Source OCR Engine"
    license = "Apache-2.0"
    homepage = "https://github.com/tesseract-ocr/tesseract"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("leptonica/1.87.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable training tools (requires pango/cairo not available)
        tc.variables["BUILD_TRAINING_TOOLS"] = False
        # Disable graphics (ScrollView) for headless build
        tc.variables["GRAPHICS_DISABLED"] = True
        # Allow older cmake policies
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["tesseract"]
        self.cpp_info.includedirs = ["include"]
        # C++ standard library needed when linking static libtesseract.a
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++"]
