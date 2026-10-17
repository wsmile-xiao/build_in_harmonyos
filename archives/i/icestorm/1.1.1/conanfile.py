#!/usr/bin/env python3
"""Conan recipe for Project IceStorm 1.1.1.

1.1.1 is 1.1 plus the iCE40 device databases (share/icebox/chipdb-*.txt).
Upstream ships those as build-time generated files, not as source files, so
1.1 packaged none of them; see notes.md.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save


class IcestormConan(ConanFile):
    name = "icestorm"
    version = "1.1.1"
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

# The iCE40 device databases are build products, not source files: upstream's
# icebox/Makefile generates them by running icebox_chipdb.py, and only the
# generator is shipped in the release tarball.  nextpnr's ice40 backend reads
# <ICEBOX_DATADIR>/chipdb-<device>.txt, and icetime resolves the same names
# relative to its own binary, so the databases have to be generated here and
# installed next to the timing tables.
set(chipdb_devices 384 1k 8k 5k lm4k u4k)
set(chipdb_flags   "-3" "" "-8" "-5" "-4" "-u")
set(chipdb_databases)
list(LENGTH chipdb_devices chipdb_count)
math(EXPR chipdb_last "${chipdb_count} - 1")
foreach(i RANGE ${chipdb_last})
  list(GET chipdb_devices ${i} chipdb_device)
  list(GET chipdb_flags   ${i} chipdb_flag)
  separate_arguments(chipdb_flag_args UNIX_COMMAND "${chipdb_flag}")
  set(chipdb_output "${CMAKE_CURRENT_BINARY_DIR}/chipdb-${chipdb_device}.txt")
  execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/icebox/icebox_chipdb.py" ${chipdb_flag_args}
    OUTPUT_FILE "${chipdb_output}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/icebox"
    COMMAND_ERROR_IS_FATAL ANY)
  list(APPEND chipdb_databases "${chipdb_output}")
endforeach()

add_executable(icetime
  icetime/icetime.cc
  icetime/iceutil.cc
  ${timing_sources})
# CHIPDB_SUBDIR is the path *below* share/ (upstream config.mk:
# CHIPDB_SUBDIR ?= $(PROGRAM_PREFIX)icebox).  The code builds
# PREFIX "/share/" CHIPDB_SUBDIR and <bindir>/../share/ CHIPDB_SUBDIR, so a
# leading /share here yields share//share/icebox and matches nothing.
target_compile_definitions(icetime PRIVATE
  PREFIX="${CMAKE_INSTALL_PREFIX}"
  CHIPDB_SUBDIR="icebox")
target_link_libraries(icetime PRIVATE m)
install(TARGETS icetime RUNTIME DESTINATION bin)
install(FILES ${chipdb_databases} DESTINATION share/icebox)
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
        self._run_upstream_icebox_checks()

    def _run_upstream_icebox_checks(self):
        """Run upstream's icebox/Makefile `check` target.

        It consists of three pure-Python self-tests that need no Yosys:
        tc_logic_xpr.py round-trips every LUT value through the logic-expression
        converters, while tc_xlat_netnames.py and tc_rxlat_netnames.py exercise
        netname translation in both directions.  The latter two load the chipdb
        databases, so they also prove the databases generated above are readable
        by icebox.py.  Upstream runs them with the databases in icebox/, which is
        why they are copied there first.
        """
        icebox_src = os.path.join(self.source_folder, "icebox")
        generated = glob.glob(
            os.path.join(self.build_folder, "**", "chipdb-*.txt"),
            recursive=True,
        )
        for path in generated:
            shutil.copy2(path, os.path.join(icebox_src, os.path.basename(path)))
        for script in ("tc_logic_xpr.py", "tc_xlat_netnames.py",
                       "tc_rxlat_netnames.py"):
            self.run("python3 %s" % script, cwd=icebox_src)

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
