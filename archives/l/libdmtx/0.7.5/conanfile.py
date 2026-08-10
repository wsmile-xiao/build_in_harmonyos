#!/usr/bin/env python3
"""Conan recipe for libdmtx 0.7.5 — Data Matrix barcode reading/writing library.

libdmtx 0.7.5 ships only autotools build files, which are unavailable on OHOS
(missing automake/libtool). This recipe generates a CMakeLists.txt in source()
adapted from the upstream v0.7.8 CMake build to enable CMake-based compilation.
"""
from conan import ConanFile
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibdmtxConan(ConanFile):
    name = "libdmtx"
    version = "0.7.5"
    description = "Data Matrix barcode reading/writing library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/dmtx/libdmtx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # v0.7.5 does not ship CMakeLists.txt; autotools is unavailable on OHOS.
        # Write a CMakeLists.txt (adapted from upstream v0.7.8) to enable CMake build.
        save(self, "CMakeLists.txt", CMAKELISTS_TXT)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["DMTX_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["DMTX_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["dmtx"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]


CMAKELISTS_TXT = r"""cmake_minimum_required(VERSION 3.5)
project(DMTX VERSION 0.7.5 LANGUAGES C)

set(DEFAULT_SHARED_LIBS "ON")
if(DEFINED BUILD_SHARED_LIBS AND NOT BUILD_SHARED_LIBS STREQUAL "")
    set(DEFAULT_SHARED_LIBS "${BUILD_SHARED_LIBS}")
endif()
option(DMTX_SHARED "Build DMTX as shared library" "${DEFAULT_SHARED_LIBS}")
if(DMTX_SHARED)
  add_library(dmtx_shared SHARED "dmtx.c")
  set_target_properties(dmtx_shared PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
  )
  target_link_libraries(dmtx_shared PUBLIC m)
  set_target_properties(dmtx_shared PROPERTIES PUBLIC_HEADER "${CMAKE_CURRENT_SOURCE_DIR}/dmtx.h" OUTPUT_NAME "dmtx")
  install(TARGETS dmtx_shared LIBRARY ARCHIVE RUNTIME PUBLIC_HEADER)
endif()

set(DEFAULT_STATIC_LIBS "ON")
if(DEFINED BUILD_STATIC_LIBS AND NOT BUILD_STATIC_LIBS STREQUAL "")
    set(DEFAULT_STATIC_LIBS "${BUILD_STATIC_LIBS}")
endif()
option(DMTX_STATIC "Build DMTX as static library" "${DEFAULT_STATIC_LIBS}")
if(DMTX_STATIC)
  add_library(dmtx_static STATIC "dmtx.c")
  target_link_libraries(dmtx_static PUBLIC m)
  set_target_properties(dmtx_static PROPERTIES PUBLIC_HEADER "${CMAKE_CURRENT_SOURCE_DIR}/dmtx.h" OUTPUT_NAME "dmtx")
  install(TARGETS dmtx_static LIBRARY ARCHIVE RUNTIME PUBLIC_HEADER)
endif()

add_compile_definitions(VERSION="${PROJECT_VERSION}")

include(CheckIncludeFile)
include(CheckFunctionExists)
check_include_file(sys/time.h HAVE_SYS_TIME_H)
check_function_exists(gettimeofday HAVE_GETTIMEOFDAY)
if(HAVE_SYS_TIME_H)
  add_compile_definitions(HAVE_SYS_TIME_H)
endif()
if(HAVE_GETTIMEOFDAY)
  add_compile_definitions(HAVE_GETTIMEOFDAY)
endif()
"""
