#!/usr/bin/env python3
"""Conan recipe for mpack-msgpack 1.1.1.

MPack is a C encoder/decoder for the MessagePack serialization format
(ludocode/mpack). The upstream source does not include a build system for
creating a library (its build system is only for running unit tests). This
recipe generates a CMakeLists.txt in build() to compile the mpack source
files into a static library, using the Conan CMakeToolchain for
cross-compilation support (R33).
"""
import os

from conan import ConanFile
from conan.tools.files import get, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MpackMsgpackConan(ConanFile):
    name = "mpack-msgpack"
    version = "1.1.1"
    description = "C encoder/decoder for the MessagePack serialization format"
    license = "MIT"
    homepage = "https://github.com/ludocode/mpack"
    url = "https://github.com/ludocode/mpack"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        # mpack has no CMakeLists.txt for building a library; create one
        cmake_lists = (
            "cmake_minimum_required(VERSION 3.15)\n"
            "project(mpack C)\n"
            "\n"
            "set(MPACK_SOURCES\n"
            "    src/mpack/mpack-common.c\n"
            "    src/mpack/mpack-expect.c\n"
            "    src/mpack/mpack-node.c\n"
            "    src/mpack/mpack-platform.c\n"
            "    src/mpack/mpack-reader.c\n"
            "    src/mpack/mpack-writer.c\n"
            ")\n"
            "\n"
            "add_library(mpack ${MPACK_SOURCES})\n"
            "target_include_directories(mpack PUBLIC src/mpack)\n"
            "\n"
            "install(TARGETS mpack\n"
            "    ARCHIVE DESTINATION lib\n"
            "    LIBRARY DESTINATION lib\n"
            ")\n"
            "install(DIRECTORY src/mpack/ DESTINATION include\n"
            "    FILES_MATCHING PATTERN \"*.h\"\n"
            ")\n"
        )
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_lists)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mpack"]
