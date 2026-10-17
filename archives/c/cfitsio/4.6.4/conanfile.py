#!/usr/bin/env python3
"""Conan recipe for cfitsio 4.6.4.

CFITSIO is a library of C and Fortran subroutines for reading and writing
data files in FITS (Flexible Image Transport System) data format. This recipe
builds the static library (R26: cfitsio is a system-name library, static by
default to avoid polluting /lib /lib64) with zlib support and all optional
network/compression backends (curl, bzip2, pthreads) disabled for a minimal,
self-contained build.

Build system: CMake (autotools is avoided because of HMDFS limitations on
this platform — config.status failures and cat/stdout redirection issues).
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CfitsioConan(ConanFile):
    name = "cfitsio"
    version = "4.6.4"
    description = (
        "Library of C and Fortran subroutines for reading and writing data "
        "files in FITS (Flexible Image Transport System) data format."
    )
    license = "CFITSIO"  # ISC-like custom license
    homepage = "https://heasarc.gsfc.nasa.gov/docs/fitsio/"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_curl": [True, False],
    }
    default_options = {
        "shared": False,
        "with_curl": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cfitsio unconditionally requires zlib (FIND_PACKAGE(ZLIB REQUIRED)).
        # Pull it as a static dependency to keep the package self-contained.
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: system-name library — default to static to avoid emitting a
        # libcfitsio.so that would collide with a system-installed copy.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Minimal, self-contained build: disable every optional backend that
        # would introduce extra runtime dependencies (curl, bzip2, pthreads).
        tc.variables["USE_CURL"] = "ON" if self.options.with_curl else "OFF"
        tc.variables["USE_PTHREADS"] = "OFF"
        tc.variables["USE_BZIP2"] = "OFF"
        # No test programs / utility binaries in the packaged library.
        tc.variables["TESTS"] = "OFF"
        tc.variables["UTILS"] = "OFF"
        # Position-independent code so the static archive can be linked into
        # shared objects / Python extension modules by consumers.
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        # HarmonyOS / OHOS platform quirk: CMake's FIND_LIBRARY(M_LIB m) does
        # not resolve on this unknown-system target (it reports NOTFOUND and
        # then fails generation). The math symbols live in libm, so set it
        # explicitly. Done via the toolchain (R33: no reliance on shell env).
        tc.variables["M_LIB"] = "m"
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
        self.cpp_info.libs = ["cfitsio"]
        self.cpp_info.set_property("cmake_file_name", "cfitsio")
        self.cpp_info.set_property("cmake_target_name", "cfitsio::cfitsio")
        self.cpp_info.set_property("pkg_config_name", "cfitsio")
        # cfitsio links against libm on POSIX platforms (R32: include OHOS).
        if str(self.settings.os) in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
