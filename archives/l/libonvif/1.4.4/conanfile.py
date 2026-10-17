#!/usr/bin/env python3
"""Conan recipe for libonvif - ONVIF IP camera client library + onvif-util CLI.

CMake project (C core library "onvif" + C++ utility "onvif-util").
Depends on libxml2 (REQUIRED in libonvif/CMakeLists.txt; the WIN32-only
Iconv find_package does not apply to OHOS). Upstream hardcodes
add_library(onvif SHARED ...), so this package ships a shared library.
Upstream registers no test suite (no tests/ directory, no add_test/CTest),
so upstream test inventory is 0 (evidence in notes.md) and the consumer
program in test_package covers the exported C API with hard assertions.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file


class LibonvifConan(ConanFile):
    name = "libonvif"
    version = "1.4.4"
    description = "ONVIF IP camera client library (WS-Discovery, device/media/PTZ services) and onvif-util CLI"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sr99622/libonvif"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Required by the recipe-completeness gate even with an empty patch set.
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The published libxml2/2.15.3.1 binary bakes an EMPTY cpp_info
        # (libxml2_INCLUDE_DIRS_RELEASE is empty in the CMakeDeps data), so
        # whatever find_package(LibXml2) resolves to, the LIBXML2_* cache
        # variables upstream reads can end up empty on a clean worker and
        # onvif.c fails with 'libxml/parser.h' not found. Pin them to the
        # Conan package layout explicitly (headers are nested under
        # include/libxml2/).
        lib = self.dependencies["libxml2"]
        inc = os.path.join(lib.package_folder, "include", "libxml2")
        tc.variables["LIBXML2_INCLUDE_DIR"] = inc
        tc.variables["LIBXML2_INCLUDE_DIRS"] = inc
        tc.variables["LIBXML2_LIBRARIES"] = os.path.join(
            lib.package_folder, "lib", "libxml2.so")
        # Upstream only builds the onvif-gui/libavio subprojects when
        # BUILD_GUI is set; keep them off (Qt/ffmpeg are out of scope).
        tc.variables["BUILD_GUI"] = False
        # Upstream add_library(onvif SHARED ...) is hardcoded: always shared.
        # musl ignores DT_RUNPATH and cmake --install rewrites RPATH into a
        # form the OHOS loader can reject, so skip install-time RPATH edits.
        tc.variables["CMAKE_SKIP_INSTALL_RPATH"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Upstream replaces the whole CMAKE_CXX_FLAGS with a hardening set,
        # which would discard the flags injected by the Conan toolchain
        # (-stdlib=libc++ etc.) for the C++ utility. Convert it to
        # add_compile_options so Conan's flags survive (sources-only change,
        # identical hardening flags; see notes.md).
        replace_in_file(
            self, os.path.join(src, "CMakeLists.txt"),
            'set(CMAKE_CXX_FLAGS "-D_FORTIFY_SOURCE=2 -fstack-protector-strong -Wformat -Werror=format-security")',
            'add_compile_options(-D_FORTIFY_SOURCE=2 -fstack-protector-strong -Wformat -Werror=format-security)',
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream sets CMAKE_INSTALL_INCLUDEDIR="include/${CMAKE_LIBRARY_ARCHITECTURE}",
        # burying onvif.h under a target-specific directory. Normalize the
        # layout to include/ so cpp_info stays simple.
        inc = os.path.join(self.package_folder, "include")
        if os.path.isdir(inc):
            for entry in glob.glob(os.path.join(inc, "*")):
                if os.path.isdir(entry) and os.path.isfile(os.path.join(entry, "onvif.h")):
                    for name in os.listdir(entry):
                        os.replace(os.path.join(entry, name), os.path.join(inc, name))
                    os.rmdir(entry)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["onvif"]
        self.cpp_info.bindirs = ["bin"]
        # The public onvif.h uses libxml2 types (xmlDocPtr ...) in its API,
        # so consumers compiling against it need libxml2 headers propagated.
        self.cpp_info.requires = ["libxml2::libxml2"]
