#!/usr/bin/env python3
"""Conan recipe — error-detection 2.1.1 (Checksum & CRC library, aKaReZa75).

Pure C library providing 8/16/32-bit checksums and configurable CRC-8/16/32.
Upstream ships no build system (only Sources/err.c + err.h); a minimal
CMakeLists.txt is injected at source() time. err.h's external aKaReZa.h
framework include is replaced by the 0001 patch with stdint/stdbool plus the
bit macros required by err.c (portability, same generic definitions as the
upstream STM32 variant of aKaReZa.h).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ErrorDetectionConan(ConanFile):
    name = "error-detection"
    version = "2.1.1"
    description = "Error Detection Library (8/16/32-bit checksum & CRC-8/16/32) for embedded communication protocols"
    license = "GPL-3.0"
    homepage = "https://github.com/aKaReZa75/Error_Detection"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 注入 CMakeLists.txt（上游仓库没有构建系统）
        cmakelists = '''cmake_minimum_required(VERSION 3.15)
project(error-detection VERSION 2.1.1 LANGUAGES C)

add_library(error-detection Sources/err.c)
target_include_directories(error-detection PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/Sources>
    $<INSTALL_INTERFACE:include>
)

set_target_properties(error-detection PROPERTIES
    PUBLIC_HEADER "Sources/err.h"
    C_STANDARD 99
    C_STANDARD_REQUIRED ON
    POSITION_INDEPENDENT_CODE ON
)

include(GNUInstallDirs)

install(TARGETS error-detection
    EXPORT error-detectionTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT error-detectionTargets
    FILE error-detectionTargets.cmake
    NAMESPACE error-detection::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/error-detection
)
'''
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmakelists)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["error-detection"]
        self.cpp_info.set_property("cmake_file_name", "error-detection")
        self.cpp_info.set_property("cmake_target_name", "error-detection::error-detection")
