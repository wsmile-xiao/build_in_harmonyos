#!/usr/bin/env python3
"""Conan recipe for easylogger 2.2.0.

EasyLogger (armink/EasyLogger) is an embedded C logging library. The
official 2.2.0 tarball has no configure script and no library build
target: it ships `easylogger/src/*.c` (core) + `easylogger/inc/*.h`
(headers) + `easylogger/port/elog_port.c` (empty per-platform template)
and per-platform demos. This recipe generates a small CMakeLists.txt
(same pattern as the linenoise / easyflash recipes) to build and install
the static library and public headers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches


class EasyloggerConan(ConanFile):
    name = "easylogger"
    version = "2.2.0"
    description = "A lightweight C logging library for embedded and desktop systems"
    license = "MIT"
    homepage = "https://github.com/armink/EasyLogger"
    url = "https://github.com/armink/EasyLogger"

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

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Upstream ships no library build target; provide a CMake build.
        # Core sources: easylogger/src/*.c. The per-platform port template
        # (easylogger/port/elog_port.c) is an empty stub that consumers
        # replace for their target, so it is NOT compiled into the library.
        cmake_content = """cmake_minimum_required(VERSION 3.15)
project(easylogger C)

file(GLOB ELOG_CORE_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/easylogger/src/*.c")

add_library(easylogger ${ELOG_CORE_SOURCES})
add_library(easylogger::easylogger ALIAS easylogger)
target_include_directories(easylogger PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/easylogger/inc
    ${CMAKE_CURRENT_SOURCE_DIR}/easylogger/plugins)
find_package(Threads REQUIRED)
target_link_libraries(easylogger PUBLIC Threads::Threads)

install(TARGETS easylogger
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib)
install(FILES
    ${CMAKE_CURRENT_SOURCE_DIR}/easylogger/inc/elog.h
    ${CMAKE_CURRENT_SOURCE_DIR}/easylogger/inc/elog_cfg.h
    DESTINATION include)
install(FILES
    ${CMAKE_CURRENT_SOURCE_DIR}/easylogger/plugins/file/elog_file.h
    ${CMAKE_CURRENT_SOURCE_DIR}/easylogger/plugins/file/elog_file_cfg.h
    ${CMAKE_CURRENT_SOURCE_DIR}/easylogger/plugins/flash/elog_flash.h
    ${CMAKE_CURRENT_SOURCE_DIR}/easylogger/plugins/flash/elog_flash_cfg.h
    DESTINATION include)
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["easylogger"]
        self.cpp_info.set_property("cmake_file_name", "easylogger")
        self.cpp_info.set_property("cmake_target_name", "easylogger::easylogger")
