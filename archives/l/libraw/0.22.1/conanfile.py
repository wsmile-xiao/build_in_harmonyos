#!/usr/bin/env python3
"""Conan recipe — LibRaw 0.22.1: RAW image processing library.

LibRaw is a library for reading RAW files from digital photo cameras
(CR2, NEF, ARW, DNG, ...).  It provides a C++ API (class LibRaw) and a C
API (libraw_open_file / libraw_dcraw_process / ...).  Two libraries are
built:
  - raw    — non-thread-safe (single-threaded, LIBRAW_NOTHREADS define)
  - raw_r  — reentrant / thread-safe (linked with pthreads)

Build system: CMake.  The upstream 0.22.1 release tarball ships only
Autotools (configure.ac + Makefile.am) with no pre-generated `configure`
script.  Autoreconf requires aclocal/automake which are unavailable on
OHOS CI workers.  A self-contained CMakeLists.txt is added via a
portability patch, replacing the Autotools path entirely.

Dependencies (Conan, published on ohpcd):
  - zlib/1.3.1.1   — deflate-compressed DNG support
  - libjpeg/10     — lossy-compressed DNG / JPEG thumbnail support
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibrawConan(ConanFile):
    name = "libraw"
    version = "0.22.1"
    description = "LibRaw — library for reading and processing RAW image files"
    license = "LGPL-2.1"
    homepage = "https://www.libraw.org/"
    url = ""  # CI fills this

    # Library (libraw.so/libraw.a + libraw_r.so/libraw_r.a).  When examples
    # are enabled, CLI tools (dcraw_emu, raw-identify, ...) are also built
    # and installed to bin/ (R38: commands.json declared at software level).
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "enable_jpeg": [True, False],
        "enable_zlib": [True, False],
        "enable_examples": [True, False],
    }
    default_options = {
        "shared": True,
        "enable_jpeg": True,
        "enable_zlib": True,
        "enable_examples": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.enable_zlib:
            self.requires("zlib/1.3.1.1")
        if self.options.enable_jpeg:
            self.requires("libjpeg/10")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libraw is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps feeds ZLIB::ZLIB / JPEG::JPEG targets into the CMake build.
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # Map conan options to CMake cache variables.  ENABLE_ZLIB and
        # ENABLE_JPEG are forwarded so the options actually control the build
        # (the CMakeLists gates find_package(REQUIRED) on them).  When OFF the
        # CMake side defines NO_JPEG / skips USE_ZLIB instead of silently
        # pulling in host-system libs.
        tc.cache_variables["ENABLE_EXAMPLES"] = self.options.enable_examples
        tc.cache_variables["ENABLE_ZLIB"] = self.options.enable_zlib
        tc.cache_variables["ENABLE_JPEG"] = self.options.enable_jpeg
        # R26: static build → BUILD_SHARED_LIBS=OFF (Conan manages the
        # dependency chain; avoids polluting system /lib with same-name .so).
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9: -j1 — parallel make hits HMDFS jobserver fifo EPERM (E074).
        cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Both the single-threaded (raw) and reentrant (raw_r) libs.
        self.cpp_info.libs = ["raw", "raw_r"]
        # raw_r needs pthread
        self.cpp_info.system_libs = ["pthread", "m"]
        if self.options.enable_examples:
            self.cpp_info.bindirs = ["bin"]
