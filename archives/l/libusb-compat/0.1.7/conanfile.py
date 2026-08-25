#!/usr/bin/env python3
"""Conan recipe for libusb-compat 0.1.7 (OHOS CMake build).

Upstream libusb-compat ships only an autotools build system, which fails
on HarmonyOS due to HMDFS hmmac restrictions on temporary file operations.
This recipe creates a custom CMakeLists.txt in source() so the library
can be built with CMake on OHOS.

Dependency: libusb/1.0.27 (the underlying USB access library).
"""

import os
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save, replace_in_file


class LibusbCompatConan(ConanFile):
    name = "libusb-compat"
    version = "0.1.7"
    description = "Compatibility layer providing libusb-0.1 API on top of libusb-1.0"
    license = "LGPL-2.1-or-later"
    homepage = "https://libusb.info/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self,
            url=self.conan_data["sources"][self.version]["url"],
            sha256=self.conan_data["sources"][self.version]["sha256"],
            filename="libusb-compat-0.1.7.tar.gz",
            strip_root=True)
        self._create_cmake_build_system()

    def _create_cmake_build_system(self):
        """Create CMakeLists.txt and config.h.cmake for OHOS build.

        Upstream only provides autotools.  HMDFS hmmac blocks mktemp etc.,
        so we generate a CMake build system instead.
        """
        # --- CMakeLists.txt ---
        cmake = textwrap.dedent("""\
            cmake_minimum_required(VERSION 3.10)
            project(libusb-compat VERSION 0.1.7)

            # Conan CMakeDeps generates libusb-1.0Config.cmake with target
            # libusb-1.0::libusb-1.0 (the recipe sets cmake_file_name).
            find_package(libusb-1.0 CONFIG REQUIRED)

            option(ENABLE_LOG "Enable logging" ON)
            option(ENABLE_DEBUG_LOG "Enable debug logging" OFF)

            configure_file(
                ${CMAKE_CURRENT_SOURCE_DIR}/config.h.cmake
                ${CMAKE_CURRENT_BINARY_DIR}/config.h
            )

            set(LIBUSB_COMPAT_SOURCES libusb/core.c)
            add_library(usb ${LIBUSB_COMPAT_SOURCES})

            target_include_directories(usb
                PUBLIC
                    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
                    $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>
                    $<INSTALL_INTERFACE:include>
            )

            target_compile_options(usb PRIVATE
                -fvisibility=hidden -std=gnu99
                -Wall -Wundef -Wunused
                -Wstrict-prototypes -Werror-implicit-function-declaration
            )

            target_link_libraries(usb PRIVATE libusb-1.0::libusb-1.0 ${CMAKE_DL_LIBS})

            # LT_MAJOR=8, LT_REVISION=4, LT_AGE=4 -> soversion 4.4.4
            set_target_properties(usb PROPERTIES
                VERSION 4.4.4 SOVERSION 0.1 OUTPUT_NAME usb
            )

            # pkg-config file
            set(prefix ${CMAKE_INSTALL_PREFIX})
            set(exec_prefix "\\${prefix}")
            set(libdir "\\${exec_prefix}/lib")
            set(includedir "\\${prefix}/include")
            set(VERSION ${PROJECT_VERSION})
            configure_file(
                ${CMAKE_CURRENT_SOURCE_DIR}/libusb.pc.in
                ${CMAKE_CURRENT_BINARY_DIR}/libusb.pc @ONLY
            )

            install(TARGETS usb
                LIBRARY DESTINATION lib
                ARCHIVE DESTINATION lib
                RUNTIME DESTINATION bin
            )
            install(FILES libusb/usb.h DESTINATION include)
            install(FILES ${CMAKE_CURRENT_BINARY_DIR}/libusb.pc
                    DESTINATION lib/pkgconfig)
        """)
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake)

        # --- config.h.cmake ---
        config_h = textwrap.dedent("""\
            #ifndef CONFIG_H
            #define CONFIG_H

            #define PACKAGE "libusb-compat"
            #define PACKAGE_VERSION "0.1.7"
            #define VERSION "0.1.7"
            #define LIBUSB01_VERSION "0.1.12"
            #define API_EXPORTED __attribute__((visibility("default")))

            #cmakedefine ENABLE_LOGGING
            #cmakedefine ENABLE_DEBUG_LOGGING

            #endif /* CONFIG_H */
        """)
        save(self, os.path.join(self.source_folder, "config.h.cmake"), config_h)

        # --- Fix libusb.pc.in: use @VERSION@ instead of @LIBUSB01_VERSION@ ---
        replace_in_file(
            self,
            os.path.join(self.source_folder, "libusb.pc.in"),
            "Version: @LIBUSB01_VERSION@",
            "Version: @VERSION@",
        )

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        if self.settings.os in ("Linux", "OHOS"):
            # CI worker has no bare 'ld'; force lld so CMake compiler
            # detection can link its test program.
            tc.variables["CMAKE_C_FLAGS"] = "-fuse-ld=lld"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The library is named "libusb" (not "libusb-compat") to match
        # upstream's installed filename (-lusb) and its pkg-config name.
        self.cpp_info.libs = ["usb"]
        self.cpp_info.set_property("pkg_config_name", "libusb")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
