#!/usr/bin/env python3
"""Conan recipe for RapidJSON 1.1.0 — header-only C++ JSON library.

RapidJSON is a header-only library. No compilation is needed.
The recipe downloads the source and copies headers + CMake config files.
Since CMake does not recognize HarmonyOS as a valid platform, we skip
CMake configure and manually install headers and config files.

Upstream tests (Google Test suite under test/unittest/) are compiled
and run in build() to provide HMBS verification evidence.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, save, export_conandata_patches
from conan.tools.layout import basic_layout



class RapidjsonConan(ConanFile):
    name = "rapidjson"
    version = "1.1.0"
    description = "A fast JSON parser/generator for C++ with both SAX and DOM style APIs"
    license = "MIT"
    homepage = "https://rapidjson.org/"
    url = ""

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._vendor_gtest()

    def _vendor_gtest(self):
        """Vendor Google Test 1.8.1 sources into thirdparty/gtest/googletest.

        RapidJSON's upstream FindGTestSrc.cmake searches
        ``${CMAKE_CURRENT_LIST_DIR}/../thirdparty/gtest/googletest`` for
        ``CMakeLists.txt`` and ``src/gtest_main.cc``. The release tarball
        ships an empty ``thirdparty/gtest`` git submodule, so without
        vendoring, ``find_package(GTestSrc)`` fails and the upstream test
        subtree is skipped entirely (discovered=0, executed=0).

        We unpack the googletest subtree of gtest release-1.8.1 into
        ``thirdparty/gtest/googletest`` to satisfy the find-module lookup.
        """
        gtest_dir = os.path.join(self.source_folder, "thirdparty", "gtest")
        target_googletest = os.path.join(gtest_dir, "googletest")
        if os.path.exists(os.path.join(target_googletest, "CMakeLists.txt")):
            return  # Already vendored

        # Download the gtest source archive using Conan's tooling.
        gtest_data = self.conan_data.get("gtest")
        if not gtest_data:
            raise ConanException("gtest source entry missing from conandata.yml")

        # Use a temp download under the source tree.
        os.makedirs(gtest_dir, exist_ok=True)
        tmp_dir = os.path.join(self.source_folder, "_hmbs_gtest_dl")
        os.makedirs(tmp_dir, exist_ok=True)
        get(self, url=gtest_data["url"], sha256=gtest_data["sha256"],
            strip_root=True, destination=tmp_dir)

        # The googletest-1.8.1 archive contains a top-level ``googletest/``
        # directory alongside ``googlemock/``. We only need the googletest
        # subtree (CMakeLists.txt, src/gtest_main.cc, include/gtest/gtest.h).
        dl_googletest = os.path.join(tmp_dir, "googletest")
        if not os.path.isdir(dl_googletest):
            # Some archives may nest under a version dir; search for it.
            for root, dirs, _ in os.walk(tmp_dir):
                if os.path.basename(root) == "googletest":
                    dl_googletest = root
                    break
        if not os.path.isdir(dl_googletest):
            raise ConanException("could not locate googletest/ subtree in vendored gtest archive")

        # Move the unpacked googletest/ into thirdparty/gtest/googletest.
        if os.path.exists(target_googletest):
            shutil.rmtree(target_googletest)
        shutil.move(dl_googletest, target_googletest)

        # Best-effort cleanup of the scratch download dir.
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    def build(self):
        # Header-only library: no compilation needed for the library itself.
        # Upstream Google Test suite is compiled and run in test_package/test()
        # (see test_package/conanfile.py) because that lifecycle hook always
        # executes, whereas build() is skipped when the binary package is
        # already cached (``Already installed!``). Running upstream tests in
        # test_package guarantees HMBS_UPSTREAM_TEST_RESULT is produced on
        # every ``conan create`` regardless of cache state.
        pass

    def package(self):
        # Copy headers
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

        # Generate and install CMake config files
        # This allows downstream CMake projects to use find_package(RapidJSON)
        cmake_dir = os.path.join(self.package_folder, "lib", "cmake", "RapidJSON")

        # RapidJSONConfig.cmake
        rapidjson_config = (
            '# Generated by Conan for RapidJSON 1.1.0\n'
            '# Header-only library: no library targets to link\n'
            '\n'
            'include(CMakeFindDependencyMacro)\n'
            '\n'
            '# Compute the include directory relative to this config file\n'
            'get_filename_component(RapidJSON_CMAKE_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)\n'
            'get_filename_component(RapidJSON_LIB_DIR "${RapidJSON_CMAKE_DIR}" PATH)\n'
            'get_filename_component(RapidJSON_PREFIX "${RapidJSON_LIB_DIR}" PATH)\n'
            'get_filename_component(RapidJSON_PREFIX "${RapidJSON_PREFIX}" PATH)\n'
            'set(RapidJSON_INCLUDE_DIR "${RapidJSON_PREFIX}/include")\n'
            '\n'
            '# Create the imported target\n'
            'if(NOT TARGET RapidJSON::RapidJSON)\n'
            '    add_library(RapidJSON::RapidJSON INTERFACE IMPORTED)\n'
            '    set_target_properties(RapidJSON::RapidJSON PROPERTIES\n'
            '        INTERFACE_INCLUDE_DIRECTORIES "${RapidJSON_INCLUDE_DIR}"\n'
            '    )\n'
            'endif()\n'
            '\n'
            'set(RapidJSON_FOUND ON)\n'
        )
        save(self, os.path.join(cmake_dir, "RapidJSONConfig.cmake"), rapidjson_config)

        # RapidJSONConfigVersion.cmake
        rapidjson_config_version = (
            '# Generated by Conan for RapidJSON 1.1.0\n'
            'set(PACKAGE_VERSION "1.1.0")\n'
            '\n'
            'if("${PACKAGE_FIND_VERSION}" VERSION_EQUAL "${PACKAGE_VERSION}")\n'
            '    set(PACKAGE_VERSION_EXACT TRUE)\n'
            '    set(PACKAGE_VERSION_COMPATIBLE TRUE)\n'
            'endif()\n'
            '\n'
            'if("${PACKAGE_FIND_VERSION}" VERSION_LESS "${PACKAGE_VERSION}")\n'
            '    set(PACKAGE_VERSION_COMPATIBLE TRUE)\n'
            'endif()\n'
            '\n'
            '# CMake requires PACKAGE_VERSION_COMPATIBLE=TRUE when no version is requested\n'
            'if(NOT DEFINED PACKAGE_FIND_VERSION)\n'
            '    set(PACKAGE_VERSION_COMPATIBLE TRUE)\n'
            'endif()\n'
        )
        save(self, os.path.join(cmake_dir, "RapidJSONConfigVersion.cmake"),
             rapidjson_config_version)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "RapidJSON")
        self.cpp_info.set_property("cmake_target_name", "RapidJSON::RapidJSON")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link
        self.cpp_info.libs = []