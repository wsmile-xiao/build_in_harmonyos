#!/usr/bin/env python3
"""Conan recipe — ngt 2.8.0 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

NGT (Neighborhood Graph and Tree) is Yahoo Japan's high-speed approximate
nearest neighbor (ANN) search C++ library. It builds two libraries
(libngt.so shared + libngt.a static) plus the command-line tools `ngt` and
`qbg`.

Adaptation notes for HarmonyOS (OHOS, aarch64):
  * CMake does not recognise "HarmonyOS" as a UNIX-like platform, so
    CMAKE_SYSTEM_NAME is overridden to "Linux" (same approach as many other
    OHOS recipes in this repo; the OHOS SDK clang still targets
    aarch64-unknown-linux-ohos via the toolchain).
  * OpenMP is provided by the OHOS SDK clang toolchain itself
    (-fopenmp=libomp), so no separate conan OpenMP dependency is needed.
  * QBG (NGTQ) needs BLAS/LAPACK; OpenBLAS is used as the provider. NGT's
    CMake linked the raw names "lapack"/"blas", which we changed to the
    find_package(BLAS/LAPACK) result variables (see patches/0002).
  * OHOS's dynamic loader cannot load a shared library through a symlink,
    so package() turns the libngt.so.2 SONAME symlink into a real file
    (same fix as knowledge entry E316).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class NgtConan(ConanFile):
    name = "ngt"
    version = "2.8.0"
    description = ("NGT (Neighborhood Graph and Tree) — Yahoo Japan's high-speed "
                   "approximate nearest neighbor search C++ library")
    license = "Apache-2.0"
    homepage = "https://github.com/NGT-labs/NGT"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os checks must use in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ngt only supports os=Linux/OHOS, current: {self.settings.os}")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"ngt recipe targets aarch64 (armv8), current arch: {self.settings.arch}")

    def requirements(self):
        # QBG (NGTQ) needs BLAS + LAPACK; OpenBLAS provides both sets of symbols
        # (sgemm_/dgemm_ etc. are called by NGTQ/Matrix.h).
        self.requires("openblas/0.3.34")
        # NGT is built with OpenMP (-fopenmp=libomp); make the LLVM OpenMP
        # runtime an explicit conan dependency so consumer/test runtimes can
        # resolve libomp.so (E127: libomp/15.0.4 is the OHOS ported runtime).
        self.requires("libomp/15.0.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            # E092: CMake doesn't treat HarmonyOS/OHOS as a UNIX-like platform;
            # NGT's whole build is guarded by if(UNIX). Pretend Linux and let the
            # OHOS SDK toolchain keep its aarch64-unknown-linux-ohos target.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Avoid -march=native (build-host CPU flags are invalid for the target
        # even when building natively on an OHOS aarch64 device in CI).
        tc.cache_variables["NGT_MARCH_NATIVE_DISABLED"] = True
        # Point find_package(BLAS)/find_package(LAPACK) at the OpenBLAS library
        # (full path; patches/0002 links the found libraries instead of -llapack).
        openblas_lib = os.path.join(
            self.dependencies["openblas"].package_folder, "lib", "libopenblas.so")
        tc.cache_variables["BLAS_LIBRARIES"] = openblas_lib
        tc.cache_variables["LAPACK_LIBRARIES"] = openblas_lib
        tc.generate()

    def build(self):
        # OHOS make jobserver FIFO cannot be created under /storage, but GNU
        # make falls back to normal parallel jobs; cap at 4 to keep CI sane.
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "4"
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The OHOS loader refuses to load a shared library through a symlink
        # (knowledge E316), and HMDFS blocks symlink creation from conan build
        # contexts, so NGT is built unversioned (patches/0003) and libngt.so is
        # already a real file. Defence in depth: if a symlink ever appears,
        # replace it with a real copy.
        libdir = os.path.join(self.package_folder, "lib")
        soname_file = os.path.join(libdir, "libngt.so")
        real_files = [os.path.join(libdir, f)
                      for f in ("libngt.so.2.8.0", "libngt.so.2", "libngt.so.1")]
        real = next((p for p in real_files if os.path.isfile(p)), None)
        if os.path.islink(soname_file) and real:
            os.remove(soname_file)
            shutil.copy2(real, soname_file)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ngt")
        self.cpp_info.set_property("cmake_target_name", "ngt::ngt")
        self.cpp_info.set_property("pkg_config_name", "ngt")
        self.cpp_info.libs = ["ngt"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["pthread", "m"]
