#!/usr/bin/env python3
"""Conan recipe for ALGLIB 4.7.0.

The upstream C++ GPL source archive uses the 4.07.0 file/version string while
the task board normalizes it as 4.7.0. Upstream ships source files and tests but
no build system, so this recipe generates a small CMake project to build the
library and upstream test executables.
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, download, save, unzip


class AlglibConan(ConanFile):
    name = "alglib"
    version = "4.7.0"
    description = "C++ numerical analysis library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.alglib.net/"
    url = "https://www.alglib.net/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("alglib is adapted for Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        filename = os.path.basename(source["url"])
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self.output.info("Downloading %s" % source["url"])
        archive_path = os.path.join(self.source_folder, filename)
        download(self, source["url"], archive_path,
                 sha256=source["sha256"], headers=headers)
        unzip(self, archive_path, strip_root=True)

    def generate(self):
        self._write_cmake_project()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["ALGLIB_TARGET_CPU"] = self._target_cpu
        if "fPIC" in self.options:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "gpl*.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "alglib")
        self.cpp_info.set_property("cmake_target_name", "alglib::alglib")
        self.cpp_info.set_property("pkg_config_name", "alglib")
        self.cpp_info.libs = ["alglib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    @property
    def _target_cpu(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "armv8.3"):
            return "AE_AARCH64"
        if arch in ("x86", "x86_64"):
            return "AE_INTEL"
        return "AE_UNKNOWN"

    def _write_cmake_project(self):
        cmake_lists = r"""
cmake_minimum_required(VERSION 3.15)
project(alglib CXX)

include(CTest)
find_package(Threads REQUIRED)

if(NOT DEFINED ALGLIB_TARGET_CPU)
    set(ALGLIB_TARGET_CPU AE_UNKNOWN)
endif()

file(GLOB ALGLIB_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")

set(ALGLIB_DEFINITIONS
    AE_OS=AE_POSIX
    AE_THREADING=AE_SERIAL
    AE_CPU=${ALGLIB_TARGET_CPU}
    ALGLIB_NO_FAST_KERNELS
)

set(ALGLIB_NO_EXCEPTIONS_DEFINITIONS
    AE_OS=AE_UNKNOWN
    AE_THREADING=AE_SERIAL_UNSAFE
    AE_CPU=${ALGLIB_TARGET_CPU}
    ALGLIB_NO_FAST_KERNELS
    AE_NO_EXCEPTIONS
)

add_library(alglib ${ALGLIB_SOURCES})
target_include_directories(alglib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
    $<INSTALL_INTERFACE:include/alglib>
)
target_compile_definitions(alglib PUBLIC ${ALGLIB_DEFINITIONS})
target_link_libraries(alglib PUBLIC Threads::Threads m)

set(ALGLIB_TESTS test_i test_c test_x test_xpart0)
foreach(test_name IN LISTS ALGLIB_TESTS)
    add_executable(${test_name} "tests/${test_name}.cpp")
    target_link_libraries(${test_name} PRIVATE alglib)
    add_test(NAME ${test_name} COMMAND ${test_name})
endforeach()

add_library(alglib_no_exceptions OBJECT ${ALGLIB_SOURCES})
target_include_directories(alglib_no_exceptions PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src")
target_compile_definitions(alglib_no_exceptions PUBLIC ${ALGLIB_NO_EXCEPTIONS_DEFINITIONS})

add_executable(test_xne "tests/test_xne.cpp" $<TARGET_OBJECTS:alglib_no_exceptions>)
target_include_directories(test_xne PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
target_compile_definitions(test_xne PRIVATE ${ALGLIB_NO_EXCEPTIONS_DEFINITIONS})
target_link_libraries(test_xne PRIVATE m)
add_test(NAME test_xne COMMAND test_xne)

install(TARGETS alglib
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)
install(DIRECTORY src/ DESTINATION include/alglib FILES_MATCHING PATTERN "*.h")
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"),
             textwrap.dedent(cmake_lists).lstrip())
