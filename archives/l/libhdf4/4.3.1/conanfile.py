#!/usr/bin/env python3
"""Conan recipe for HDF4 4.3.1."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get, replace_in_file, save


class Libhdf4Conan(ConanFile):
    name = "libhdf4"
    version = "4.3.1"
    description = "HDF4 scientific data format and library"
    license = "HDF"
    homepage = "https://www.hdfgroup.org/solutions/hdf4/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg/10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _upstream_source(self):
        nested = os.path.join(self.source_folder, "hdf-4.3.1")
        return nested if os.path.isfile(os.path.join(nested, "CMakeLists.txt")) else self.source_folder

    @staticmethod
    def _static_library_filename(library):
        if library.endswith((".a", ".lib")):
            return library
        if library.startswith("lib"):
            return f"{library}.a"
        return f"lib{library}.a"

    def _dependency_static_library(self, dependency_name, fallback_library):
        dependency = self.dependencies[dependency_name]
        library_dirs = list(dependency.cpp_info.libdirs) or [
            os.path.join(dependency.package_folder, "lib")
        ]
        libraries = list(dependency.cpp_info.libs) or [fallback_library]
        return os.path.join(
            library_dirs[0],
            self._static_library_filename(libraries[0]),
        ).replace(os.sep, "/")

    def generate(self):
        CMakeDeps(self).generate()
        jpeg = self.dependencies["libjpeg"]
        jpeg_include = os.path.join(jpeg.package_folder, "include").replace(os.sep, "/")
        jpeg_library = self._dependency_static_library("libjpeg", "jpeg")
        find_jpeg = "\n".join(
            [
                "set(JPEG_FOUND TRUE)",
                f'set(JPEG_INCLUDE_DIR "{jpeg_include}")',
                'set(JPEG_INCLUDE_DIRS "${JPEG_INCLUDE_DIR}")',
                f'set(JPEG_LIBRARY "{jpeg_library}")',
                'set(JPEG_LIBRARIES "${JPEG_LIBRARY}")',
                "if(NOT TARGET JPEG::JPEG)",
                "  add_library(JPEG::JPEG STATIC IMPORTED)",
                "  set_target_properties(JPEG::JPEG PROPERTIES",
                '    IMPORTED_LOCATION "${JPEG_LIBRARY}"',
                '    INTERFACE_INCLUDE_DIRECTORIES "${JPEG_INCLUDE_DIR}")',
                "endif()",
                "",
            ]
        )
        save(self, os.path.join(self.generators_folder, "FindJPEG.cmake"), find_jpeg)

        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_MODULE_PATH"] = self.generators_folder.replace(os.sep, "/")
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_STATIC_LIBS"] = True
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.variables["HDF4_BUILD_TOOLS"] = False
        toolchain.variables["HDF4_BUILD_NETCDF_TOOLS"] = False
        toolchain.variables["HDF4_BUILD_EXAMPLES"] = False
        toolchain.variables["HDF4_BUILD_FORTRAN"] = False
        toolchain.variables["HDF4_BUILD_JAVA"] = False
        toolchain.variables["HDF4_BUILD_UTILS"] = False
        toolchain.variables["HDF4_ENABLE_SZIP_SUPPORT"] = False
        toolchain.variables["HDF4_MODULE_MODE_JPEG"] = True
        toolchain.variables["HDF4_MODULE_MODE_ZLIB"] = False
        toolchain.variables["HDF4_USE_ZLIB_STATIC"] = True
        toolchain.generate()

    def build(self):
        source_dir = self._upstream_source()
        replace_in_file(
            self,
            os.path.join(source_dir, "CMakeFilters.cmake"),
            "set(H4_ZLIB_FOUND ZLIB_FOUND})",
            "set(H4_ZLIB_FOUND ${ZLIB_FOUND})",
            strict=True,
        )
        cmake = CMake(self)
        cmake.configure(build_script_folder=source_dir)
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
            "COPYING",
            src=self._upstream_source(),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["mfhdf", "hdf"]
        self.cpp_info.requires = ["zlib::zlib", "libjpeg::libjpeg"]
        self.cpp_info.set_property("cmake_file_name", "HDF4")
        self.cpp_info.set_property("cmake_target_name", "HDF4::HDF4")
