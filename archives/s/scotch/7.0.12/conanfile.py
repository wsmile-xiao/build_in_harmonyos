#!/usr/bin/env python3
"""Conan recipe for SCOTCH 7.0.12."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ScotchConan(ConanFile):
    name = "scotch"
    version = "7.0.12"
    description = "Graph and mesh partitioning library"
    license = "CECILL-C"
    homepage = "https://gitlab.inria.fr/scotch/scotch"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("SCOTCH supports Linux and OHOS")

    def requirements(self):
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("zlib/1.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _library(folder, names):
        for name in names:
            matches = glob.glob(os.path.join(folder, "lib", name))
            if matches:
                return matches[0]
        return os.path.join(folder, "lib", names[0])

    def generate(self):
        CMakeDeps(self).generate()
        bzip2 = self.dependencies["bzip2"].package_folder
        xz = self.dependencies["xz"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        bzip2_library = self._library(bzip2, ["libbz2.a", "libbz2.so"])
        lzma_library = self._library(xz, ["liblzma.a", "liblzma.so"])
        zlib_library = self._library(zlib, ["libz.a", "libz.so"])
        tc = CMakeToolchain(self)
        tc.cache_variables["BZIP2_INCLUDE_DIR"] = os.path.join(bzip2, "include")
        tc.cache_variables["BZIP2_INCLUDE_DIRS"] = os.path.join(bzip2, "include")
        tc.cache_variables["BZIP2_LIBRARY"] = bzip2_library
        tc.cache_variables["BZIP2_LIBRARIES"] = bzip2_library
        tc.cache_variables["LIBLZMA_INCLUDE_DIR"] = os.path.join(xz, "include")
        tc.cache_variables["LIBLZMA_INCLUDE_DIRS"] = os.path.join(xz, "include")
        tc.cache_variables["LIBLZMA_LIBRARY"] = lzma_library
        tc.cache_variables["LIBLZMA_LIBRARIES"] = lzma_library
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = os.path.join(zlib, "include")
        tc.cache_variables["ZLIB_INCLUDE_DIRS"] = os.path.join(zlib, "include")
        tc.cache_variables["ZLIB_LIBRARY"] = zlib_library
        tc.cache_variables["ZLIB_LIBRARIES"] = zlib_library
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_FORTRAN"] = False
        tc.variables["BUILD_PTSCOTCH"] = False
        tc.variables["BUILD_LIBESMUMPS"] = False
        tc.variables["BUILD_LIBSCOTCHMETIS"] = False
        tc.variables["ENABLE_TESTS"] = True
        tc.variables["THREADS"] = True
        tc.variables["USE_ZLIB"] = True
        tc.variables["USE_LZMA"] = True
        tc.variables["USE_BZ2"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure -j1'
            )

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE_en.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["scotch", "scotcherr"]
        self.cpp_info.set_property("cmake_file_name", "scotch")
        self.cpp_info.set_property("cmake_target_name", "scotch::scotch")
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["m", "pthread"]
