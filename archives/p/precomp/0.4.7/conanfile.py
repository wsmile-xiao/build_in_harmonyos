#!/usr/bin/env python3
"""Conan recipe — precomp 0.4.7 (CMake, command-line precompressor).

precomp scans already-compressed streams (deflate/zlib/gzip, bZip2, GIF, JPG,
MP3, ZIP, PDF, SWF, MIME Base64, LZMA) inside a file, undoes the inner
compression into a .pcf container so a stronger compressor (xz/7z) can do a
better job, and restores the original file bit-to-bit identically with -r.

All third-party codecs (bzip2, zlib, giflib, liblzma, packJPG, packMP3,
preflate) are vendored under contrib/ and compiled into the single
`precomp` executable, so the recipe has zero conan requirements; the only
external dependency is pthreads (find_package(Threads)), provided by musl.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PrecompConan(ConanFile):
    name = "precomp"
    version = "0.4.7"
    description = (
        "Command-line precompressor: converts already-compressed streams "
        "(deflate/zlib/gzip, bZip2, GIF, JPG, MP3, ZIP, PDF, LZMA) into .pcf "
        "files that compress better, with bit-to-bit lossless restore"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/schnaader/precomp-cpp"
    url = "https://github.com/schnaader/precomp-cpp"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 3.2), which CMake
        # 4.x refuses to configure; keep the legacy project buildable.
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMake has no OHOS/HarmonyOS platform module: the UNIX variable
        # stays undefined and precomp's `if (UNIX)` branch (platform defines
        # -DUNIX/-DLINUX plus find_package(Threads)) never runs, so the code
        # would take Windows paths.  The tool is built natively on OHOS with
        # clang against musl/libc++ and uses no Linux-specific APIs, so
        # configure it as a generic Linux platform (abcmidi precedent).
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMakeLists.txt defines only add_executable() with no
        # install() rule, so stage the single binary manually.
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        shutil.copy(os.path.join(self.build_folder, "precomp"), bindir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
