#!/usr/bin/env python3
"""Conan recipe for mini_chromium — Chromium base library minimal subset."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

class MiniChromiumConan(ConanFile):
    name = "mini_chromium"
    version = "1.0"
    description = "Minimal subset of Chromium base library (logging, strings, files, threading)"
    license = "BSD-3-Clause"
    homepage = "https://chromium.googlesource.com/chromium/mini_chromium"
    url = ""
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
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake_content = r"""
cmake_minimum_required(VERSION 3.16)
project(mini_chromium VERSION 1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
file(GLOB_RECURSE MINI_CHROMIUM_SOURCES
  "${CMAKE_CURRENT_SOURCE_DIR}/base/*.cc"
)
list(FILTER MINI_CHROMIUM_SOURCES EXCLUDE REGEX "(_win|_mac|_ios|_apple|_fuchsia|_android)\\.cc$|/(apple|mac|ios|fuchsia|win|android)/")
add_library(mini_chromium ${MINI_CHROMIUM_SOURCES})
target_include_directories(mini_chromium
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
    $<INSTALL_INTERFACE:include/mini_chromium>
)
if(UNIX)
  target_link_libraries(mini_chromium PUBLIC pthread)
endif()
include(GNUInstallDirs)
install(TARGETS mini_chromium
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(DIRECTORY base/
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/mini_chromium/base
  FILES_MATCHING PATTERN "*.h"
)
install(DIRECTORY build/
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/mini_chromium/build
  FILES_MATCHING PATTERN "*.h"
)
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_content)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mini_chromium"]
        self.cpp_info.includedirs = ["include", "include/mini_chromium"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
