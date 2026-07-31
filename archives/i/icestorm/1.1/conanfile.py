#!/usr/bin/env python3
"""Conan recipe for Project IceStorm 1.1."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save


class IcestormConan(ConanFile):
    name = "icestorm"
    version = "1.1"
    description = "Open-source tools for the Lattice iCE40 FPGA bitstream format"
    license = "ISC"
    homepage = "https://github.com/YosysHQ/icestorm"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("icestorm supports POSIX targets")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        cmake_lists = r"""
cmake_minimum_required(VERSION 3.20)
project(icestorm LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

foreach(tool IN ITEMS icepack icemulti icepll icebram)
  add_executable(${tool} ${tool}/${tool}.cc)
  target_link_libraries(${tool} PRIVATE m)
  install(TARGETS ${tool} RUNTIME DESTINATION bin)
endforeach()

set(timing_sources)
foreach(chip IN ITEMS lp384 lp1k lp8k hx1k hx8k up5k u4k)
  set(output "${CMAKE_CURRENT_BINARY_DIR}/timings-${chip}.cc")
  execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/icetime/timings.py" "${chip}"
    OUTPUT_FILE "${output}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/icetime"
    COMMAND_ERROR_IS_FATAL ANY)
  list(APPEND timing_sources "${output}")
endforeach()

add_executable(icetime
  icetime/icetime.cc
  icetime/iceutil.cc
  ${timing_sources})
target_compile_definitions(icetime PRIVATE
  PREFIX="${CMAKE_INSTALL_PREFIX}"
  CHIPDB_SUBDIR="/share/icebox")
target_link_libraries(icetime PRIVATE m)
install(TARGETS icetime RUNTIME DESTINATION bin)
install(DIRECTORY icebox/
  DESTINATION share/icebox
  FILES_MATCHING PATTERN "chipdb-*.txt")
install(DIRECTORY icefuzz/
  DESTINATION share/icebox
  FILES_MATCHING PATTERN "timings_*.txt")
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_lists)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        bin_dir = os.path.join(self.package_folder, "bin")
        shutil.copy2(
            os.path.join(bin_dir, "icepack"),
            os.path.join(bin_dir, "iceunpack"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
