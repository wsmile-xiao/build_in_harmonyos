#!/usr/bin/env python3
"""Conan recipe for STIFF 2.4.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save


class StiffConan(ConanFile):
    name = "stiff"
    version = "2.4.0"
    description = "FITS-to-TIFF scientific image converter"
    license = "GPL-3.0-or-later"
    homepage = "https://www.astromatic.net/software/stiff/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("stiff supports POSIX targets")

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg/10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["stiff"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["libtiff"],
            destination="libtiff-src",
            strip_root=True,
        )

    def _upstream_source(self):
        nested = os.path.join(self.source_folder, "stiff-2.4.0")
        return nested if os.path.isdir(os.path.join(nested, "src")) else self.source_folder

    def _libtiff_source(self):
        root = os.path.join(self._upstream_source(), "libtiff-src")
        nested = os.path.join(root, "tiff-4.7.2")
        return nested if os.path.isfile(os.path.join(nested, "CMakeLists.txt")) else root

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        zlib = self.dependencies["zlib"]
        jpeg = self.dependencies["libjpeg"]
        toolchain.variables["ZLIB_INCLUDE_DIR"] = os.path.join(
            zlib.package_folder, "include"
        ).replace(os.sep, "/")
        toolchain.variables["ZLIB_LIBRARY"] = os.path.join(
            zlib.package_folder, "lib", "libz.a"
        ).replace(os.sep, "/")
        toolchain.variables["JPEG_INCLUDE_DIR"] = os.path.join(
            jpeg.package_folder, "include"
        ).replace(os.sep, "/")
        toolchain.variables["JPEG_LIBRARY"] = os.path.join(
            jpeg.package_folder, "lib", "libjpeg.a"
        ).replace(os.sep, "/")
        toolchain.generate()

    def build(self):
        source_dir = self._upstream_source()
        libtiff_dir = self._libtiff_source().replace(os.sep, "/")
        project_dir = os.path.join(source_dir, "conan-cmake")
        save(
            self,
            os.path.join(project_dir, "config.h"),
            """#pragma once
#define DATE "2026-07-30"
#define HAVE_ATEXIT 1
#define HAVE_FCNTL_H 1
#define HAVE_FSEEKO 1
#define HAVE_GETENV 1
#define HAVE_GETPAGESIZE 1
#define HAVE_INTTYPES_H 1
#define HAVE_ISNAN2 1
#define HAVE_LIBM 1
#define HAVE_LIBTIFF 1
#define HAVE_LONG_LONG_INT 1
#define HAVE_MEMMOVE 1
#define HAVE_MEMORY_H 1
#define HAVE_MEMSET 1
#define HAVE_MMAP 1
#define HAVE_MUNMAP 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRCHR 1
#define HAVE_STRCSPN 1
#define HAVE_STRFTIME 1
#define HAVE_STRINGS_H 1
#define HAVE_STRING_H 1
#define HAVE_STRPBRK 1
#define HAVE_STRRCHR 1
#define HAVE_STRSPN 1
#define HAVE_STRTOL 1
#define HAVE_SYS_MMAN_H 1
#define HAVE_SYS_PARAM_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_TIME_H 1
#define HAVE_UNISTD_H 1
#define HAVE_UNSIGNED_LONG_LONG_INT 1
#define LIBTIFF_H <tiffio.h>
#define PACKAGE "stiff"
#define PACKAGE_NAME "STIFF"
#define PACKAGE_STRING "STIFF 2.4.0"
#define PACKAGE_TARNAME "stiff"
#define PACKAGE_VERSION "2.4.0"
#define STDC_HEADERS 1
#define THREADS_NMAX 1
#define VERSION "2.4.0"
#define XSL_URL "."
#define _FILE_OFFSET_BITS 64
#define _LARGEFILE_SOURCE 1
""",
        )
        cmake_project = """cmake_minimum_required(VERSION 3.16)
project(stiff VERSION 2.4.0 LANGUAGES C)

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(tiff-tools OFF CACHE BOOL "" FORCE)
set(tiff-tests OFF CACHE BOOL "" FORCE)
set(tiff-docs OFF CACHE BOOL "" FORCE)
set(tiff-contrib OFF CACHE BOOL "" FORCE)
set(tiff-opengl OFF CACHE BOOL "" FORCE)
set(tiff-cxx OFF CACHE BOOL "" FORCE)
set(zlib ON CACHE BOOL "" FORCE)
set(jpeg ON CACHE BOOL "" FORCE)
set(libdeflate OFF CACHE BOOL "" FORCE)
set(zstd OFF CACHE BOOL "" FORCE)
set(webp OFF CACHE BOOL "" FORCE)
set(lerc OFF CACHE BOOL "" FORCE)
set(jbig OFF CACHE BOOL "" FORCE)
set(lzma OFF CACHE BOOL "" FORCE)
add_subdirectory("@LIBTIFF_DIR@" libtiff-build)

set(STIFF_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/..")
set(FITS_SOURCES
    "${STIFF_SOURCE_DIR}/src/fits/fitsbody.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitscat.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitscheck.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitscleanup.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitsconv.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitshead.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitskey.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitsmisc.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitsread.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitstab.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitsutil.c"
    "${STIFF_SOURCE_DIR}/src/fits/fitswrite.c")

add_library(stiff_fits STATIC ${FITS_SOURCES})
target_compile_features(stiff_fits PRIVATE c_std_99)
target_compile_definitions(stiff_fits PRIVATE HAVE_CONFIG_H)
target_compile_options(stiff_fits PRIVATE -fcommon)
target_include_directories(stiff_fits PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}"
    "${STIFF_SOURCE_DIR}/src"
    "${STIFF_SOURCE_DIR}/src/fits")

add_executable(stiff
    "${STIFF_SOURCE_DIR}/src/datamem.c"
    "${STIFF_SOURCE_DIR}/src/field.c"
    "${STIFF_SOURCE_DIR}/src/image.c"
    "${STIFF_SOURCE_DIR}/src/main.c"
    "${STIFF_SOURCE_DIR}/src/makeit.c"
    "${STIFF_SOURCE_DIR}/src/prefs.c"
    "${STIFF_SOURCE_DIR}/src/threads.c"
    "${STIFF_SOURCE_DIR}/src/tiff.c"
    "${STIFF_SOURCE_DIR}/src/xml.c")
target_compile_features(stiff PRIVATE c_std_99)
target_compile_definitions(stiff PRIVATE HAVE_CONFIG_H)
target_compile_options(stiff PRIVATE -fcommon -Wno-error=format-security)
target_include_directories(stiff PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}"
    "${STIFF_SOURCE_DIR}/src"
    "${STIFF_SOURCE_DIR}/src/fits")
target_link_libraries(stiff PRIVATE stiff_fits tiff m)

install(TARGETS stiff RUNTIME DESTINATION bin)
""".replace("@LIBTIFF_DIR@", libtiff_dir)
        save(
            self,
            os.path.join(project_dir, "CMakeLists.txt"),
            cmake_project,
        )
        cmake = CMake(self)
        cmake.configure(build_script_folder=project_dir)
        cmake.build()

    def package(self):
        copy(
            self,
            "stiff",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self._upstream_source(),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
