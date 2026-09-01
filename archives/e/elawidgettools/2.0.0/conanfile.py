#!/usr/bin/env python3
"""Conan recipe for ElaWidgetTools 2.0.0."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout

class ElaWidgetToolsConan(ConanFile):
    name = "elawidgettools"
    version = "2.0.0"
    description = "Fluent-UI for Qt-Widget, based on Qt Fluent Design style component library"
    license = "MIT"
    homepage = "https://github.com/Liniyous/ElaWidgetTools"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
    def layout(self):
        cmake_layout(self)
    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ELAWIDGETTOOLS_BUILD_STATIC_LIB"] = "OFF" if self.options.shared else "ON"
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_pkg = qt5.package_folder
        tc.variables["QT5_BIN_DIR"] = os.path.join(qt5_pkg, "bin")
        qt_ver = ".".join(str(qt5.ref.version).split(".")[:3])
        for short_name, mod_dir in (("CORE", "QtCore"), ("GUI", "QtGui"), ("WIDGETS", "QtWidgets")):
            tc.variables[f"QT5_{short_name}_PRIVATE_INC"] = os.path.join(qt5_pkg, "include", mod_dir, qt_ver, mod_dir)
            tc.variables[f"QT5_{short_name}_BASE_INC"] = os.path.join(qt5_pkg, "include", mod_dir, qt_ver)
        tc.generate()
        CMakeDeps(self).generate()
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    def package(self):
        CMake(self).install()
    def package_info(self):
        self.cpp_info.libs = ["ElaWidgetTools"]
        self.cpp_info.libdirs = ["ElaWidgetTools/lib"]
        self.cpp_info.includedirs = ["ElaWidgetTools/include"]
