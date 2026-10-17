#!/usr/bin/env python3
"""Conan recipe for GLM 1.0.3, a header-only C++ mathematics library."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GlmConan(ConanFile):
    name = "glm"
    version = "1.0.3"
    description = "OpenGL Mathematics header-only C++ mathematics library"
    license = "MIT"
    homepage = "https://github.com/g-truc/glm"
    url = ""

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        source_archive = os.getenv("GLM_SOURCE_ARCHIVE")
        if source_archive:
            archive_path = Path(source_archive).resolve()
            if not archive_path.is_file():
                raise ConanInvalidConfiguration(
                    f"GLM_SOURCE_ARCHIVE is not a regular file: {archive_path}"
                )
            source["url"] = archive_path.as_uri()
            source["filename"] = archive_path.name
        get(self, **source, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["GLM_BUILD_LIBRARY"] = "OFF"
        tc.cache_variables["GLM_BUILD_TESTS"] = "OFF"
        tc.cache_variables["GLM_BUILD_INSTALL"] = "ON"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "glm")
        self.cpp_info.set_property("cmake_target_name", "glm::glm")
        self.cpp_info.set_property("pkg_config_name", "glm")
