#!/usr/bin/env python3
"""Conan recipe for libformfactor 0.4.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get, save


class LibformfactorConan(ConanFile):
    name = "libformfactor"
    version = "0.4.0"
    description = "Fourier shape transforms for polyhedral particles"
    license = "GPL-3.0-or-later"
    homepage = "https://jugit.fz-juelich.de/mlz/libformfactor"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["formfactor"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["libheinz"],
            destination=os.path.join(self.source_folder, "libheinz-src"),
            strip_root=True,
        )

    def generate(self):
        heinz_include = os.path.join(self.source_folder, "libheinz-src")
        config = "\n".join(
            [
                "set(LibHeinz_FOUND TRUE)",
                'set(LibHeinz_VERSION "4.0.0")',
                f'set(LibHeinz_INCLUDE_DIR "{heinz_include.replace(os.sep, "/")}")',
                "if(NOT TARGET LibHeinz::LibHeinz)",
                "  add_library(LibHeinz::LibHeinz INTERFACE IMPORTED)",
                "  set_target_properties(LibHeinz::LibHeinz PROPERTIES",
                '    INTERFACE_INCLUDE_DIRECTORIES "${LibHeinz_INCLUDE_DIR}")',
                "endif()",
                "",
            ]
        )
        save(self, os.path.join(self.generators_folder, "LibHeinzConfig.cmake"), config)
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.variables["PEDANTIC"] = False
        toolchain.variables["WERROR"] = False
        toolchain.variables["LibHeinz_DIR"] = self.generators_folder.replace(
            os.sep, "/"
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        ctest_env = Environment()
        ctest_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        ctest_env.define("CTEST_PARALLEL_LEVEL", "1")
        with ctest_env.vars(self).apply():
            cmake.test()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "libheinz-src", "heinz"),
            dst=os.path.join(self.package_folder, "include", "heinz"),
        )
        config_dir = os.path.join(self.package_folder, "lib", "cmake", "LibHeinz")
        config = "\n".join(
            [
                "get_filename_component(_heinz_prefix \"${CMAKE_CURRENT_LIST_DIR}/../../..\" ABSOLUTE)",
                'set(LibHeinz_INCLUDE_DIR "${_heinz_prefix}/include")',
                'set(LibHeinz_VERSION "4.0.0")',
                "set(LibHeinz_FOUND TRUE)",
                "if(NOT TARGET LibHeinz::LibHeinz)",
                "  add_library(LibHeinz::LibHeinz INTERFACE IMPORTED)",
                "  set_target_properties(LibHeinz::LibHeinz PROPERTIES",
                '    INTERFACE_INCLUDE_DIRECTORIES "${LibHeinz_INCLUDE_DIR}")',
                "endif()",
                "",
            ]
        )
        save(self, os.path.join(config_dir, "LibHeinzConfig.cmake"), config)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["formfactor"]
        self.cpp_info.set_property("cmake_file_name", "formfactor")
        self.cpp_info.set_property("cmake_target_name", "formfactor::formfactor")
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_build_modules", [])
        self.cpp_info.set_property("pkg_config_name", "libformfactor")
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake", "LibHeinz"))
