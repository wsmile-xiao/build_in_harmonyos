#!/usr/bin/env python3
"""Conan recipe for libde265 1.0.18 (CMake).

libde265 is an open-source H.265/HEVC video decoder library written in C++.
Built static (R26) with the decoder CLI (dec265) enabled; the SDL display
and encoder are disabled (the encoder sources are absent from the release
tarball, and SDL2 is an optional runtime dependency).

Platform note (aarch64/OHOS): the bundled ARM assembly in libde265/arm is
32-bit ARMv7-A NEON (uses r0-r12 registers and `push/pop`), which is invalid
on aarch64. The CMake build auto-detects HAVE_ARM + HAVE_NEON via
check_c_compiler_flag(-mfpu=neon). We force HAVE_NEON=FALSE so the
hevcdsp_qpel_neon.S object library is skipped; arm.cc (a pure-C stub that
registers no acceleration when HAVE_NEON is unset) still compiles, and the
decoder falls back to the portable C implementation (E016: reconfigure-no-asm).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Libde265Conan(ConanFile):
    name = "libde265"
    version = "1.0.18"
    description = "Open H.265/HEVC video codec implementation (decoder)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libde265"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libde265 has no external Conan dependencies; the C++ runtime is
        # provided by the toolchain (libc++).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: all build configuration is passed via CMakeToolchain variables,
        # not via shell environment variables.
        tc = CMakeToolchain(self)
        # R26: system-name library defaults to static to avoid polluting
        # /lib or /lib64 with a same-named shared object.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Only pass CMAKE_INSTALL_PREFIX (R1); conan drives the rest.
        # Disable optional SDL2 display backend (not available as a Conan dep).
        tc.variables["ENABLE_SDL"] = "OFF"
        # Enable the dec265 decoder CLI; the encoder sources (enc265/,
        # libde265/encoder/) are not shipped in the 1.0.18 release tarball,
        # so ENABLE_ENCODER must stay OFF.
        tc.variables["ENABLE_DECODER"] = "ON"
        tc.variables["ENABLE_ENCODER"] = "OFF"
        tc.variables["ENABLE_SHERLOCK265"] = "OFF"
        # E016: the bundled ARM assembly (libde265/arm/*.S) is ARMv7-A NEON
        # and does not assemble on aarch64. Force HAVE_NEON=FALSE to skip the
        # arm_neon object library; the decoder uses the portable C fallback.
        tc.cache_variables["HAVE_NEON"] = False
        # libde265 already sets CMAKE_POSITION_INDEPENDENT_CODE ON at the
        # project level; keep it explicit for clarity (R26/R5).
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
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
        # The CMake target is "de265" (libde265.a / -lde265); the upstream
        # pkg-config and cmake config files both expose the "de265" name.
        self.cpp_info.libs = ["de265"]
        self.cpp_info.set_property("cmake_file_name", "libde265")
        self.cpp_info.set_property("cmake_target_name", "libde265::de265")
        self.cpp_info.set_property("pkg_config_name", "libde265")
        # C++ runtime (libde265 is C++17); libc++ on OHOS/Linux-clang.
        if self.settings.os in ("Linux", "OHOS"):  # R32
            self.cpp_info.system_libs = ["pthread"]
