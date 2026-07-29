#!/usr/bin/env python3
"""Conan recipe for wxWidgets 3.2.6 — CMake build system.

wxWidgets is a cross-platform C++ GUI/utility framework.
HarmonyOS (OHOS) uses musl libc; autotools fails on OHOS, so CMake is used.

wxWidgets is a system same-name library (system may package libwx_baseu.so),
so it must be built static-only (R26) to avoid polluting system library paths.

Build: cmake + make -j1 (R9 parallel constraint on OHOS).
No external dependencies — zlib and pcre are bundled.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building
from conan.tools.scm import Git


class WxwidgetsConan(ConanFile):
    name = "wxwidgets"
    version = "3.2.6"
    description = "Cross-platform C++ GUI/utility library framework."
    license = "custom"  # wxWindows Library Licence (similar to LGPL)
    homepage = "https://www.wxwidgets.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # wxWidgets bundles zlib and pcre; no external deps

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Use official release tarball (wxWidgets-3.2.6.tar.bz2) which includes
        # git submodule sources (3rdparty/pcre, src/zlib, etc.) in the archive.
        # Do NOT use GitHub's auto-generated "Source code" tarball — those lack submodules.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # R26: wxWidgets is a system same-name library, force static build
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["wxBUILD_SHARED"] = "OFF"

        # wxWidgets-specific configuration
        tc.variables["wxBUILD_TESTS"] = "OFF"
        tc.variables["wxUSE_GUI"] = "OFF"
        tc.variables["wxUSE_XLOCALE"] = "OFF"

        # Avoid CMake policy warnings (use cache_variable for pre-project() effect)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # R1: configure params minimal — only --prefix related
        # CMAKE_INSTALL_PREFIX is set to / by Conan's CMakeToolchain automatically

        # HarmonyOS uses Unix-like syscalls; force UNIX=ON so CMake includes
        # platform source files (wxMutex/wxThread/wxDir/wxGetEnv etc. from src/unix/)
        # Without this, elseif(UNIX) in build/cmake/lib/base/CMakeLists.txt is false
        # for CMAKE_SYSTEM_NAME=HarmonyOS, skipping all BASE_UNIX sources.
        tc.cache_variables["UNIX"] = "ON"

        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if compilers:
            if "c" in compilers:
                tc.variables["CMAKE_C_COMPILER"] = compilers["c"]
            if "cxx" in compilers:
                tc.variables["CMAKE_CXX_COMPILER"] = compilers["cxx"]

        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()

        # R9: Use -j1 for parallel constraint on OHOS platform
        # But respect Conan's general job count when not on OHOS
        is_ohos = self.settings.os in ("Linux", "OHOS") and self.settings.os == "OHOS"
        if is_ohos:
            cmake.build(cli_args=["-j1"])
        else:
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # R26: system same-name library — set cmake_find_mode and pkg_config
        self.cpp_info.set_property("cmake_file_name", "wxWidgets")
        self.cpp_info.set_property("cmake_target_name", "wxWidgets::wxWidgets")
        self.cpp_info.set_property("pkg_config_name", "wx-baseu-3.2")
        
        # wxWidgets installs headers to include/wx-3.2/ and generated config to lib/wx/include/
        self.cpp_info.includedirs = [
            "include/wx-3.2",                              # wx/string.h, wx/defs.h, etc.
            "lib/wx/include/base-unicode-static-3.2",      # generated wx/setup.h
        ]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        # Library names (strip "lib" prefix and ".a" suffix)
        self.cpp_info.libs = [
            "wx_baseu-3.2",
            "wx_baseu_net-3.2",
            "wxregexu-3.2",
            "wxzlib-3.2",
        ]

        # Static build: link system libs needed by wxBase (pthread, dl)
        self.cpp_info.system_libs = ["pthread", "dl"]
        self.cpp_info.sharedlinkflags = []
        self.cpp_info.exelinkflags = []
