#!/usr/bin/env python3
"""Conan recipe — liblbfgs 1.10 (CMake wrapper, upstream v1.10 lacks CMakeLists.txt)"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class LiblbfgsConan(ConanFile):
    name = "liblbfgs"
    version = "1.10"
    description = "C library of Limited-memory BFGS (L-BFGS) optimization"
    license = "MIT"
    homepage = "https://www.chokkan.org/software/liblbfgs/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # v1.10 upstream has no CMakeLists.txt; we generate one in build()
        tc.generate()

    def _generate_cmake(self):
        """Write a minimal CMakeLists.txt since upstream v1.10 lacks one."""
        cmake = textwrap.dedent("""\
            cmake_minimum_required(VERSION 3.15)
            project(liblbfgs C)

            option(LBFGS_SHARED "Build shared library" OFF)

            if(LBFGS_SHARED)
              add_library(lbfgs SHARED lib/lbfgs.c)
            else()
              add_library(lbfgs STATIC lib/lbfgs.c)
            endif()

            target_include_directories(lbfgs PUBLIC
              $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
              $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/lib>
              $<INSTALL_INTERFACE:include>
            )
            target_compile_definitions(lbfgs PRIVATE LBFGS_FLOAT=64)

            include(GNUInstallDirs)
            install(TARGETS lbfgs
              ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
              LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
              RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
            )
            install(FILES include/lbfgs.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
        """)
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake)

    def build(self):
        apply_conandata_patches(self)
        self._generate_cmake()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "lbfgs.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.lib", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dylib", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lbfgs"]
        self.cpp_info.set_property("cmake_file_name", "LBFGS")
        self.cpp_info.set_property("cmake_target_name", "LBFGS::lib")
        self.cpp_info.set_property("pkg_config_name", "liblbfgs")
