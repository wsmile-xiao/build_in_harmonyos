#!/usr/bin/env python3
"""Conan recipe for libharu 2.3.0 (Haru Free PDF Library).

CMake build (matches upstream CMakeLists and the locally validated build).
The produced library is libhpdf (headers hpdf.h); zlib and libpng are
real published dependencies and enable Flate compression + PNG embedding.
"""

import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


def _guess_ohos_sysroot_libdir(cc):
    """Derive the OHOS sysroot lib dir from the C compiler itself.

    The OHOS clang driver locates the sysroot relative to its own install
    (visible in `clang -E -v` as `.../llvm/bin/../../sysroot/usr/include/
    <triple>`).  haru.cmake does `find_library(MATH_LIB NAMES m PATHS
    /usr/local/lib /usr/lib)` which misses the sysroot entirely, so we
    inject the sysroot's usr/lib/<triple> into CMAKE_SYSTEM_LIBRARY_PATH.
    This keeps the recipe portable: it works for any OHOS SDK install
    without hard-coding an SDK path, in both local and CI builds.
    """
    try:
        proc = subprocess.run(
            [cc, "-E", "-x", "c", "-", "-v"],
            input="",
            capture_output=True,
            text=True,
            timeout=60,
        )
        stderr = proc.stderr or ""
    except (OSError, subprocess.SubprocessError):
        return ""
    m = re.search(r"-internal-externc-isystem\s+(\S+sysroot\S*?/usr/include/[^\]\s]+)", stderr)
    if not m:
        return ""
    include_dir = m.group(1)
    # include_dir = <sysroot>/usr/include/<triple>
    triple = os.path.basename(include_dir)
    libdir = os.path.join(include_dir, "..", "..", "lib", triple)
    libdir = os.path.normpath(libdir)
    return libdir if os.path.isdir(libdir) else ""


class LibharuConan(ConanFile):
    name = "libharu"
    version = "2.3.0"
    description = "Haru Free PDF Library - 用于生成 PDF 文档的 C 库"
    license = "zlib"
    homepage = "https://github.com/libharu/libharu"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # R26: libharu is not a system-name library -> default dynamic; shared=True
    # also makes VirtualRunEnv add the package lib dir to LD_LIBRARY_PATH so
    # the test_package consumer can load libhpdf.so at runtime (E298).
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Real direct dependencies: zlib (stream compression) + libpng (PNG embedding).
        # Both are published on ohpcd for os=OHOS armv8 (verified by executor preflight).
        self.requires("zlib/1.3.2")
        self.requires("libpng/1.6.58.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # upstream cmake_minimum_required() is too old for CMake >= 3.5
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # haru.cmake find_library(MATH_LIB ... PATHS /usr/local/lib /usr/lib)
        # misses the OHOS sysroot; point CMake at the sysroot lib dir.
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cc = compilers.get("c", "clang") if compilers else "clang"
            libdir = _guess_ohos_sysroot_libdir(cc)
            if libdir:
                tc.variables["CMAKE_SYSTEM_LIBRARY_PATH"] = libdir
            # E322 / expat-validated pattern: CMake ships no Platform/HarmonyOS.cmake,
            # so CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays empty and the .so
            # would carry no DT_SONAME (W3 L5 soname gate fails) even with the
            # SOVERSION patch. Set the flag explicitly and keep SONAME relocatable
            # without versioned symlinks (HMDFS-friendly), matching attica5/azure-*.
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
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
        self.cpp_info.libs = ["hpdf"]
        # libhpdf uses libm functions (sqrt etc.) through its own link line;
        # expose -lm to consumers for static builds.
        self.cpp_info.system_libs = ["m"]