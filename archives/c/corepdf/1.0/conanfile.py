#!/usr/bin/env python3
"""Conan recipe for corepdf 1.0 — a PDF viewer using Qt6 + poppler-cpp."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import Environment


CMAKELISTS_TXT = """cmake_minimum_required(VERSION 3.16)
project(corepdf VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

# Find Qt6 (qtbase conan package provides native Qt6Config.cmake via CMAKE_PREFIX_PATH)
find_package(Qt6 REQUIRED COMPONENTS Widgets)

# Find poppler via Conan CMakeDeps (provides poppler::poppler target with poppler, poppler-cpp libs)
find_package(poppler REQUIRED)

# qpdflib - static library using poppler-cpp
add_library(qpdf STATIC
    qpdflib/qpdfwidget.cpp
    qpdflib/qpdfwidget.h
)
target_include_directories(qpdf PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/qpdflib
)
target_link_libraries(qpdf PUBLIC
    Qt6::Widgets
    poppler::poppler
)
target_compile_definitions(qpdf PRIVATE QPDFLIB_BUILD)

# corepdf - application
add_executable(corepdf
    corepdf/corepdf.cpp
    corepdf/corepdf.h
    corepdf/main.cpp
)
target_include_directories(corepdf PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/corepdf
    ${CMAKE_CURRENT_SOURCE_DIR}/qpdflib
)
target_link_libraries(corepdf PRIVATE
    qpdf
    Qt6::Widgets
    poppler::poppler
)

install(TARGETS corepdf DESTINATION bin)
"""


class CorepdfConan(ConanFile):
    name = "corepdf"
    version = "1.0"
    description = "A lightweight PDF viewer using Qt6 Widgets and poppler-cpp"
    license = "GPL-3.0"
    homepage = "https://github.com/rahmanshaber/corepdf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("poppler/25.12.0.2")
        # Override fontconfig to resolve conflict: poppler pins 2.18.1, cairo pins 2.18.1.1
        self.requires("fontconfig/2.18.1.1", override=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_AUTOMOC"] = "ON"
        # qtbase uses cmake_find_mode=none with native Qt6Config.cmake;
        # Use Environment to set CMAKE_PREFIX_PATH which cmake reads from env.
        _qt_prefix = self.dependencies["qtbase"].package_folder
        _qt_env = Environment()
        _qt_env.append_path("CMAKE_PREFIX_PATH", _qt_prefix)
        _qt_env.vars(self, scope="build").save_script("conan_qt6_prefix")
        tc.generate()
        # Generate CMakeDeps for poppler (provides poppler-config.cmake with poppler::poppler target)
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Create CMakeLists.txt in source folder (original project uses qmake, not cmake)
        _cmake_path = os.path.join(self.source_folder, "CMakeLists.txt")
        save(self, _cmake_path, CMAKELISTS_TXT)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
