#!/usr/bin/env python3
"""Conan recipe for QXlsx 1.4.7 — CMake-based Qt Excel library.

QXlsx is a C++ library for reading/writing Excel (.xlsx) files, based on Qt.
Build system: CMake (QXlsx/CMakeLists.txt in the source subdirectory).
Dependency: Qt5 (Core, Gui + GuiPrivate headers).

This recipe enforces:
  R26: BUILD_SHARED_LIBS=OFF (static linking for terminal tools)
  R27: Dependencies use @ohpcd/stable format
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QXlsxConan(ConanFile):
    name = "qxlsx"
    version = "1.4.7"
    description = "Excel file (.xlsx) reader/writer library based on Qt framework"
    license = "MIT"
    homepage = "https://github.com/QtExcel/QXlsx"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: All dependencies MUST use @ohpcd/stable format
        self.requires("qt/5.15.2@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Unix Makefiles")
        # R26: Terminal tools must be statically linked for DevBox deployment
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["QT_VERSION_MAJOR"] = "5"
        # E092: CMake doesn't recognize HarmonyOS, use Linux as platform
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # QXlsx's CMakeLists.txt is in the QXlsx/ subdirectory
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "QXlsx"))
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["QXlsxQt5"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "QXlsx")
        self.cpp_info.set_property("cmake_target_name", "QXlsx::QXlsxQt5")
