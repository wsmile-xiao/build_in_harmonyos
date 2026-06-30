#!/usr/bin/env python3
"""Conan recipe — FMILibrary 2.0.3 (CMake build system).

FMI (Functional Mock-up Interface) Library — C library for importing FMU.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, replace_in_file, save, unzip, apply_conandata_patches, export_conandata_patches


class FmilibraryConan(ConanFile):
    name = "fmilibrary"
    version = "2.0.3"
    description = "FMI (Functional Mock-up Interface) Library — C library for importing FMU (Functional Mock-up Units)"
    license = "MIT"
    homepage = "https://github.com/modelon-community/fmi-library"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # FMILibrary bundles its own dependencies (zlib, expat, minizip)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Support offline/air-gapped builds: check local cache first
        local_file = os.path.join(os.environ.get("HOME", ""), "builds", "FMILibrary-2.0.3.tar.gz")
        if os.path.exists(local_file):
            unzip(self, local_file, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.cache_variables["FMILIB_BUILD_SHARED_LIB"] = "OFF"
        tc.cache_variables["FMILIB_BUILD_STATIC_LIB"] = "ON"
        tc.cache_variables["FMILIB_BUILD_TESTS"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # Apply patches from conandata.yml (if any apply cleanly)
        try:
            apply_conandata_patches(self)
        except Exception:
            pass  # Fall through to manual fixes below

        src = self.source_folder

        # --- CMake 4.x compatibility fixes (via replace_in_file) ---

        # Fix 1: Expat CMakeLists.txt — move cmake_minimum_required before project()
        # File uses CRLF line endings, so we do two simple replacements
        replace_in_file(
            self,
            os.path.join(src, "ThirdParty/Expat/expat-2.1.0/CMakeLists.txt"),
            "project(expat)",
            "cmake_minimum_required(VERSION 3.5)",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(src, "ThirdParty/Expat/expat-2.1.0/CMakeLists.txt"),
            "cmake_minimum_required(VERSION 2.6)",
            "project(expat)",
            strict=False,
        )

        # Fix 2: fmixml.cmake — add CMAKE_POLICY_VERSION_MINIMUM for Expat sub-build
        replace_in_file(
            self,
            os.path.join(src, "Config.cmake/fmixml.cmake"),
            "-DCMAKE_SHARED_LINKER_FLAGS:STRING=${CMAKE_SHARED_LINKER_FLAGS}",
            "-DCMAKE_SHARED_LINKER_FLAGS:STRING=${CMAKE_SHARED_LINKER_FLAGS}\n\t\t-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        )
        # Fix 2b: fmixml.cmake — comment out add_dependencies with file paths (CMake 4.x)
        replace_in_file(
            self,
            os.path.join(src, "Config.cmake/fmixml.cmake"),
            "add_dependencies(expatex ${CMAKE_BINARY_DIR}/CMakeCache.txt ${FMILIBRARYHOME}/CMakeLists.txt)",
            "# CMake 4.x: add_dependencies requires target names, not file paths\n# add_dependencies(expatex ${CMAKE_BINARY_DIR}/CMakeCache.txt ${FMILIBRARYHOME}/CMakeLists.txt)",
        )

        # Fix 3: mergestaticlibs.cmake — complete rewrite for CMake 4.x
        # Replaced deprecated LOCATION property with $<TARGET_FILE:...> generator expressions
        merge_content = '''#    Copyright (C) 2012 Modelon AB

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the BSD style license.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    FMILIB_License.txt file for more details.

#    You should have received a copy of the FMILIB_License.txt file
#    along with this program. If not, contact Modelon AB <http://www.modelon.com>.

# Merge_static_libs(outlib lib1 lib2 ... libn) merges a number of static
# libs into a single static library
# Fixed for CMake 4.x compatibility: replaced deprecated LOCATION property
# with $<TARGET_FILE:...> generator expressions
function(merge_static_libs outlib )
\tset(libs ${ARGV})
\tlist(REMOVE_AT libs 0)
# Create a dummy file that the target will depend on
\tset(dummyfile ${CMAKE_CURRENT_BINARY_DIR}/${outlib}_dummy.c)
\tfile(WRITE ${dummyfile} "const char * dummy = \\"${dummyfile}\\";")

\tadd_library(${outlib} STATIC ${dummyfile})

# Use generator expression for output file path (CMake 4.x compatible)
\tset(outfile "$<TARGET_FILE:${outlib}>")

# First get the file names of the libraries to be merged
\tforeach(lib ${libs})
\t\tget_target_property(libtype ${lib} TYPE)
\t\tif(NOT libtype STREQUAL "STATIC_LIBRARY")
\t\t\tmessage(FATAL_ERROR "Merge_static_libs can only process static libraries")
\t\tendif()
# Use target name for intermediate files (not file paths)
\t\tset(objlistfile ${CMAKE_CURRENT_BINARY_DIR}/${lib}_objlist)
\t\tset(objdir ${CMAKE_CURRENT_BINARY_DIR}/${lib}_objdir)
\t\tset(extract_script ${CMAKE_CURRENT_BINARY_DIR}/${lib}_extract.cmake)
\tendforeach()

# general UNIX - need to "ar -x" and then "ar -ru"
  if(MSVC)
    # lib.exe does the merging of libraries just need to convert the list into string
\tmessage(FATAL_ERROR "MSVC merge not supported in fixed version")

  elseif(APPLE)
    # Use OSX's libtool to merge archives
\tmessage(FATAL_ERROR "APPLE merge not supported in fixed version")

  else()
  # general UNIX - need to "ar -x" and then "ar -ru"
\tmessage(STATUS "will be merging ${libs}")
\tset(extrafiles "")
\tforeach(lib ${libs})
# objlistfile will contain the list of object files for the library
\t\tset(objlistfile ${CMAKE_CURRENT_BINARY_DIR}/${lib}_objlist)
\t\tset(objdir ${CMAKE_CURRENT_BINARY_DIR}/${lib}_objdir)
\t\tset(extract_script ${CMAKE_CURRENT_BINARY_DIR}/${lib}_extract.cmake)
# Write extraction script that takes libfile as parameter
\t\tFILE(WRITE ${extract_script}
"# Extract object files from the library
message(STATUS \\"Extracting object files\\")
file(MAKE_DIRECTORY \\"\\${objdir}\\")
execute_process(COMMAND \\"\\${CMAKE_AR}\\" x \\"\\${libfile}\\" WORKING_DIRECTORY \\"\\${objdir}\\")
execute_process(COMMAND ls . WORKING_DIRECTORY \\"\\${objdir}\\" OUTPUT_FILE \\"\\${objlistfile}\\")")
\t\tfile(MAKE_DIRECTORY ${objdir})
\t\tadd_custom_command(
\t\t\t\tOUTPUT ${objlistfile}
\t\t\t\tCOMMAND ${CMAKE_COMMAND}
\t\t\t\t    -Dlibfile=$<TARGET_FILE:${lib}>
\t\t\t\t    -DCMAKE_AR=${CMAKE_AR}
\t\t\t\t    -Dobjdir=${objdir}
\t\t\t\t    -Dobjlistfile=${objlistfile}
\t\t\t\t    -P ${extract_script}
\t\t\t\tDEPENDS ${lib}
\t\t\t\tCOMMENT "Extracting object files from ${lib}")
\t\tlist(APPEND extrafiles "${objlistfile}")
\t\t# relative path is needed by ar under MSYS
\t\tfile(RELATIVE_PATH objlistfilerpath ${objdir} ${objlistfile})
\t\tadd_custom_command(TARGET ${outlib} POST_BUILD
\t\t\t\tCOMMAND ${CMAKE_COMMAND} -E echo "Running: ${CMAKE_AR} ru ${outfile} @${objlistfilerpath}"
\t\t\t\tCOMMAND ${CMAKE_AR} ru "${outfile}" @"${objlistfilerpath}"
\t\t\t\tWORKING_DIRECTORY ${objdir})
\tendforeach()
\tadd_custom_command(TARGET ${outlib} POST_BUILD
\t\t\t\tCOMMAND ${CMAKE_COMMAND} -E echo "Running: ${CMAKE_RANLIB} ${outfile}"
\t\t\t\tCOMMAND ${CMAKE_RANLIB} ${outfile})
  endif()
  file(WRITE ${dummyfile}.base "const char* ${outlib}_sublibs=\\"${libs}\\";")
  add_custom_command(
\t\t\tOUTPUT  ${dummyfile}
\t\t\tCOMMAND ${CMAKE_COMMAND}  -E copy ${dummyfile}.base ${dummyfile}
\t\t\tDEPENDS ${libs} ${extrafiles})

 endfunction()
'''
        save(self, os.path.join(src, "Config.cmake/mergestaticlibs.cmake"), merge_content)

        # Fix 4: runtime_test.cmake — replace LOCATION property with generator expression
        replace_in_file(
            self,
            os.path.join(src, "Config.cmake/runtime_test.cmake"),
            "get_property(COMPRESS_EXECUTABLE TARGET compress_test_fmu_zip PROPERTY LOCATION)",
            'set(COMPRESS_EXECUTABLE "$<TARGET_FILE:compress_test_fmu_zip>")',
        )

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Also copy license
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["fmilib"]
