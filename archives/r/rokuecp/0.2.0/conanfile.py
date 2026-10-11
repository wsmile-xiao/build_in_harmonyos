#!/usr/bin/env python3
"""Conan recipe for rokuecp 0.2.0."""

import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file


class RokuecpConan(ConanFile):
    name = "rokuecp"
    version = "0.2.0"
    description = "C library for discovering and controlling Roku devices through ECP"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/benthetechguy/rokuecp"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gssdp/1.6.6")
        self.requires("libsoup3/3.6.5-r1")
        self.requires("libxml2/2.15.3.1")
        # GSSDP's public headers include glib/gobject/gio headers.  Its
        # published cpp_info intentionally does not link the static glib2
        # archive (that would create a second GObject type system), so consume
        # glib2 directly for headers while leaving its libraries unlinked.
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=False)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["DOCS"] = False
        tc.variables["DOCS_ONLY"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["CMAKE_SKIP_INSTALL_RPATH"] = True
        glib = self.dependencies["glib2"]
        tc.variables["ROKUECP_GLIB_INCLUDE_DIRS"] = ";".join(
            [
                os.path.join(glib.package_folder, "include", "glib-2.0"),
                os.path.join(glib.package_folder, "lib", "glib-2.0", "include"),
            ]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "add_library(rokuecp SHARED rokuecp.c)",
            "add_library(rokuecp rokuecp.c)",
        )
        old = """    find_package(PkgConfig)
    pkg_check_modules(gssdp REQUIRED gssdp-1.6)
    pkg_check_modules(libsoup REQUIRED libsoup-3.0)
    pkg_check_modules(libxml2 REQUIRED libxml-2.0>=2.13)

    target_include_directories(rokuecp PRIVATE ${gssdp_INCLUDE_DIRS})
    target_include_directories(rokuecp PRIVATE ${libsoup_INCLUDE_DIRS})
    target_include_directories(rokuecp PRIVATE ${libxml2_INCLUDE_DIRS})
    target_link_libraries(rokuecp PRIVATE ${gssdp_LINK_LIBRARIES})
    target_link_libraries(rokuecp PRIVATE ${libsoup_LINK_LIBRARIES})
    target_link_libraries(rokuecp PRIVATE ${libxml2_LINK_LIBRARIES})"""
        new = """    find_package(gssdp-1.6 CONFIG REQUIRED)
    find_package(libsoup-3.0 CONFIG REQUIRED)
    find_package(LibXml2 CONFIG REQUIRED)

    target_link_libraries(rokuecp PRIVATE
        gssdp-1.6::gssdp-1.6
        libsoup-3.0::libsoup-3.0
        LibXml2::LibXml2)
    target_include_directories(rokuecp PRIVATE ${ROKUECP_GLIB_INCLUDE_DIRS})"""
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"), old, new)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._resign_shared_libraries()

    def _resign_shared_libraries(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            return
        libraries = glob.glob(os.path.join(self.package_folder, "lib", "*.so"))
        libraries += glob.glob(os.path.join(self.package_folder, "lib", "*.so.*"))
        for library in libraries:
            if os.path.islink(library):
                continue
            if os.path.isfile(objcopy):
                self.run(f'{objcopy} --remove-section .codesign "{library}"')
            self.run(f'{signer} sign -inFile "{library}" -outFile "{library}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["rokuecp"]
        self.cpp_info.set_property("cmake_file_name", "rokuecp")
        self.cpp_info.set_property("cmake_target_name", "rokuecp::rokuecp")
        self.cpp_info.set_property("pkg_config_name", "rokuecp")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
