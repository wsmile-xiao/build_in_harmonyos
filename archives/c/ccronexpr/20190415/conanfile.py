#!/usr/bin/env python3
"""Conan recipe for ccronexpr — Cron expression parsing library in C.

ccronexpr is a header-only style library with a simple .c + .h implementation.
We provide a CMakeLists.txt to build it as a static library.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class CcronexprConan(ConanFile):
    name = "ccronexpr"
    version = "20190415"
    description = "Cron expression parsing in ANSI C"
    license = "Apache-2.0"
    homepage = "https://github.com/staticlibs/ccronexpr"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # 注入 CMakeLists.txt（原始仓库没有构建系统）
        cmakelists = '''cmake_minimum_required(VERSION 3.15)
project(ccronexpr VERSION 20190415 LANGUAGES C)

add_library(ccronexpr ccronexpr.c)
target_include_directories(ccronexpr PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

set_target_properties(ccronexpr PROPERTIES
    PUBLIC_HEADER "ccronexpr.h"
    C_STANDARD 99
    POSITION_INDEPENDENT_CODE ON
)

include(GNUInstallDirs)

install(TARGETS ccronexpr
    EXPORT ccronexprTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT ccronexprTargets
    FILE ccronexprTargets.cmake
    NAMESPACE ccronexpr::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ccronexpr
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
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ccronexpr"]
        self.cpp_info.set_property("cmake_file_name", "ccronexpr")
        self.cpp_info.set_property("cmake_target_name", "ccronexpr::ccronexpr")
