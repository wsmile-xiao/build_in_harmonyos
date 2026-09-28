#!/usr/bin/env python3
"""Conan recipe for PortSMF 0.1-svn20101010."""

import json
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)


_CMAKE_LISTS = r"""
cmake_minimum_required(VERSION 3.15)
project(portsmf VERSION 0.1 LANGUAGES CXX)

include(CTest)

set(PORTSMF_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/portsmf/trunk")
set(PORTSMF_SOURCES
    "${PORTSMF_ROOT}/allegro.cpp"
    "${PORTSMF_ROOT}/allegrosmfwr.cpp"
    "${PORTSMF_ROOT}/allegrord.cpp"
    "${PORTSMF_ROOT}/allegrowr.cpp"
    "${PORTSMF_ROOT}/allegrosmfrd.cpp"
    "${PORTSMF_ROOT}/mfmidi.cpp"
    "${PORTSMF_ROOT}/strparse.cpp"
)

add_library(portsmf ${PORTSMF_SOURCES})
target_compile_features(portsmf PUBLIC cxx_std_11)
target_include_directories(portsmf PUBLIC
    $<BUILD_INTERFACE:${PORTSMF_ROOT}>
    $<INSTALL_INTERFACE:include>
)
set_target_properties(portsmf PROPERTIES
    OUTPUT_NAME portSMF
    VERSION 0.1
    SOVERSION 0
)

if(BUILD_TESTING)
    add_library(portsmf_upstream_test_object OBJECT
        "${PORTSMF_ROOT}/portsmf_test/portsmf_test.cpp"
    )
    target_compile_features(portsmf_upstream_test_object PRIVATE cxx_std_11)
    target_compile_definitions(portsmf_upstream_test_object PRIVATE
        main=portsmf_upstream_disabled_main
    )
    target_include_directories(portsmf_upstream_test_object PRIVATE
        "${PORTSMF_ROOT}"
    )

    add_executable(portsmf_upstream_tests
        $<TARGET_OBJECTS:portsmf_upstream_test_object>
        "${CMAKE_CURRENT_SOURCE_DIR}/upstream_driver.cpp"
    )
    target_compile_features(portsmf_upstream_tests PRIVATE cxx_std_11)
    target_link_libraries(portsmf_upstream_tests PRIVATE portsmf)

    foreach(case_number RANGE 1 33)
        add_test(
            NAME upstream_portsmf_test_${case_number}
            COMMAND "${CMAKE_COMMAND}" -E env
                "LD_LIBRARY_PATH=$<TARGET_FILE_DIR:portsmf>:$ENV{LD_LIBRARY_PATH}"
                "$<TARGET_FILE:portsmf_upstream_tests>" ${case_number}
        )
        set_tests_properties(upstream_portsmf_test_${case_number} PROPERTIES
            TIMEOUT 30
            WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
        )
    endforeach()
endif()

install(TARGETS portsmf
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)
install(FILES
    "${PORTSMF_ROOT}/allegro.h"
    "${PORTSMF_ROOT}/mfmidi.h"
    "${PORTSMF_ROOT}/strparse.h"
    "${PORTSMF_ROOT}/trace.h"
    DESTINATION include
)
"""


class PortsmfConan(ConanFile):
    name = "portsmf"
    version = "0.1-svn20101010"
    description = "C++ library for Standard MIDI Files and Allegro sequences"
    license = "BSD-3-Clause"
    homepage = "https://github.com/rbdannenberg/portsmf"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "upstream_driver.cpp",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=self.export_sources_folder,
        )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("portsmf is adapted for Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        save(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            textwrap.dedent(_CMAKE_LISTS).lstrip(),
        )
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = True
        if "fPIC" in self.options:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()

    def build(self):
        upstream_test = os.path.join(
            self.source_folder,
            "portsmf",
            "trunk",
            "portsmf_test",
            "portsmf_test.cpp",
        )
        # The official SVN import preserves this file with CRLF endings.
        # Normalize only its line endings so the refresh-patch-generated
        # one-line upstream test backport applies reproducibly.
        save(self, upstream_test, load(self, upstream_test))
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure',
                env="conanbuild",
            )
            result = {
                "status": "passed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": 33,
                "executed": 33,
                "passed": 33,
                "failed": 0,
                "skipped": 0,
            }
            self.output.info(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(result)}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "license.txt",
            src=os.path.join(self.source_folder, "portsmf", "trunk"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        pc_file = """prefix=${pcfiledir}/../..\nlibdir=${prefix}/lib\nincludedir=${prefix}/include\n\nName: portSMF\nDescription: Standard MIDI File and Allegro sequence library\nVersion: 0.1\nLibs: -L${libdir} -lportSMF\nCflags: -I${includedir}\n"""
        save(
            self,
            os.path.join(self.package_folder, "lib", "pkgconfig", "portSMF.pc"),
            pc_file,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "portsmf")
        self.cpp_info.set_property("cmake_target_name", "portsmf::portsmf")
        self.cpp_info.set_property("pkg_config_name", "portSMF")
        self.cpp_info.libs = ["portSMF"]
