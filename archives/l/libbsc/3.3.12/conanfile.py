#!/usr/bin/env python3
"""Conan 2 recipe for libbsc 3.3.12 (block-sorting data compression library).

Path A: pure recipe adaptation, no source patching. Upstream natively
supports AArch64 (platform.h maps __aarch64__ -> LIBBSC_CPU_FEATURE_A64;
x86 cpuid/xgetbv asm is compiled out under A64). The only build-system
shaping is toolchain variables:

- BSC_ENABLE_NATIVE_COMPILATION=OFF (E100): no -march=native, so the
  binary carries no host-CPU-specific instructions to other OHOS devices.
- BSC_ENABLE_OPENMP=OFF: the OHOS SDK ships no libomp; single-threaded
  mode is the default deliverable (round-trip verified on device).
- SONAME flags via the E322/libharu pattern: CMake has no Platform/
  HarmonyOS.cmake, so CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG stays
  empty and the .so would carry no DT_SONAME. We set the flag and
  CMAKE_PLATFORM_NO_VERSIONED_SONAME explicitly.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy

import os


class LibbscConan(ConanFile):
    name = "libbsc"
    version = "3.3.12"
    description = "High performance block-sorting data compression library (BWT-based) plus bsc CLI"
    license = "Apache-2.0"
    homepage = "https://github.com/IlyaGrebnov/libbsc"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "openmp": [True, False],
    }
    # R26: libbsc is not a system same-name library (/system/lib64/libbsc* does
    # not exist) -> default shared. shared=True also makes VirtualRunEnv add
    # the package lib dir to LD_LIBRARY_PATH so consumers load libbsc.so at
    # runtime (E298).
    default_options = {"shared": True, "fPIC": True, "openmp": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["libbsc-3.3.12.tar.gz"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # BSC_BUILD_SHARED_LIB maps the shared option onto the upstream option
        # (upstream default is OFF).
        tc.variables["BSC_BUILD_SHARED_LIB"] = "ON" if self.options.shared else "OFF"
        # E100: no -march=native — no host-CPU-tuned instructions in the artifact.
        tc.variables["BSC_ENABLE_NATIVE_COMPILATION"] = False
        # OHOS SDK ships no libomp; openmp option is off by default and only
        # turned on deliberately (requires a libomp in the sysroot).
        tc.variables["BSC_ENABLE_OPENMP"] = bool(self.options.openmp)
        tc.variables["BSC_ENABLE_CUDA"] = False
        # E322/libharu pattern: CMake ships no Platform/HarmonyOS.cmake so the
        # SONAME link flag stays empty; set it and keep the soname unversioned
        # (libbsc.so) — HMDFS-friendly, no versioned symlinks.
        if str(self.settings.os) == "OHOS":
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
        # LICENSE ships in the source root
        from conan.tools.files import copy
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libbsc")
        self.cpp_info.set_property("cmake_target_name", "libbsc::libbsc")
        self.cpp_info.set_property("pkg_config_name", "libbsc")
        # installed layout: include/libbsc/{libbsc.h,filters.h}, lib/libbsc.so, bin/bsc
        # consumers write #include <libbsc/libbsc.h>, so includedirs = include
        self.cpp_info.libs = ["bsc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]

    def package_id(self):
        del self.info.options.fPIC
