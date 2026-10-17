#!/usr/bin/env python3
"""Conan recipe for megahit 1.2.9 — metagenome assembler (CMake + OpenMP CLI).

Build: CMake. Produces three CLI executables (megahit_core / megahit_core_popcnt /
megahit_core_no_hw_accel — compile-time hw-dispatch targets) plus two python
wrapper entry points (megahit, megahit_toolkit -> megahit_core_no_hw_accel).
Links zlib (static libz.a from ohpcd) and OpenMP (clang -fopenmp=libomp on OHOS).

OHOS adaptations (patches in conandata.yml):
 - 0001: cmake_minimum_required 2.8 -> 3.5 (CMake >= 4 refuses < 3.5) and gate the
   x86-only `-mbmi2 -DUSE_BMI2 -mpopcnt` target flags behind CMAKE_SYSTEM_PROCESSOR
 - 0002: guard x86intrin.h include + BMI2 pdep to x86; add portable software pdep
 - 0003: wrapper shebang python -> python3 (no bare `python` on OHOS) and mkfifo
   fallback to regular files (named pipes return EPERM on HMDFS)
 - 0004: guard cpuid inline asm to x86; HasPopcnt/HasBmi2 return false elsewhere
   (equivalent to upstream master "support for non-x86_64 architectures", PR #368)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MegahitConan(ConanFile):
    name = "megahit"
    version = "1.2.9"
    description = ("MEGAHIT - ultra-fast and memory-efficient metagenomic "
                   "short-read de novo assembler (command line)")
    license = "GPL-3.0-only"
    homepage = "https://github.com/voutcn/megahit"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"megahit is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # megahit uses module-mode find_package(ZLIB REQUIRED); point FindZLIB
        # directly at the conan-provided zlib (R33: no shell env reliance)
        zinfo = self.dependencies["zlib"].cpp_info.aggregated_components()
        libz = None
        for d in zinfo.libdirs:
            for cand in ("libz.a", "libz.so", "libz.dylib"):
                p = os.path.join(d, cand)
                if os.path.exists(p):
                    libz = p
                    break
            if libz:
                break
        if not libz:
            raise ConanInvalidConfiguration("zlib package has no linkable library")
        tc.variables["ZLIB_INCLUDE_DIR"] = zinfo.includedirs[0]
        tc.variables["ZLIB_LIBRARY"] = libz
        # belt & suspenders: config-mode find_package(ZLIB) (CMakeDeps) would
        # leave  empty; force module mode and prime the var
        tc.variables["ZLIB_LIBRARIES"] = libz
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # R9/E074-adjacent + OpenMP compile units are memory heavy: cap at 2 jobs
        cmake.build(build_tool_args=["-j2"])

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # copy() would keep megahit_toolkit as a dangling symlink; copy real files
        for artifact in ("megahit", "megahit_toolkit", "megahit_core",
                         "megahit_core_popcnt", "megahit_core_no_hw_accel"):
            src = os.path.join(self.build_folder, artifact)
            shutil.copy2(src, os.path.join(bindir, artifact), follow_symlinks=True)

    def package_info(self):
        # standalone executables, no C/C++ library info
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
