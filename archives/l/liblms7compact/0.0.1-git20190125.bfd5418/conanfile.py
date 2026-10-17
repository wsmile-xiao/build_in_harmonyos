#!/usr/bin/env python3
"""Conan recipe for liblms7compact 0.0.1-git20190125.bfd5418 —
Compact LMS7002M driver library (XTRX SDR project).

Build system: CMake.  Upstream CMakeLists.txt is patched to:
  * require CMake >= 3.16 (CMake 4.x dropped <3.5 compatibility),
  * build with a plain Python 3 interpreter (the codegen script
    regs/enum_parser.py was rewritten without the Python 2 / Cheetah
    dependency),
  * honour BUILD_SHARED_LIBS (upstream hard-coded SHARED on non-Windows),
  * include lms7_defaults.c, which provides WEAK default implementations
    of the platform hooks (lms7_spi_transact/lms7_spi_post/lms7_log_ex)
    so the library links standalone; consumers may override them.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Liblms7CompactConan(ConanFile):
    name = "liblms7compact"
    version = "0.0.1-git20190125.bfd5418"
    description = ("Compact LMS7002M driver suitable for MCU/HOST (XTRX SDR "
                   "project), packaged as liblms7compact")
    license = "LGPL-2.1"
    homepage = "https://github.com/xtrx-sdr/liblms7002m"
    url = "https://github.com/xtrx-sdr/liblms7002m"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream liblms7002m.h guards <unistd.h> with `#ifdef __linux`.
        # HarmonyOS toolchain defines __linux__ so the header resolves there;
        # on macOS (local validation builds) we inject it explicitly.
        if self.settings.os == "Macos":
            tc.variables["CMAKE_C_FLAGS"] = "-include unistd.h"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lms7compact"]
