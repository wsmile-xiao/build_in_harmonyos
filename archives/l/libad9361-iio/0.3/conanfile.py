#!/usr/bin/env python3
"""Conan recipe for libad9361-iio - AD9361 transceiver helper library.

CMake project (C). Depends on libiio (headers + link library). The upstream
CMake file locates libiio with bare find_library()/find_path() calls, so the
recipe injects the Conan-managed libiio paths as cache variables. Of the five
upstream CTest cases, the two pure-software algorithm cases
(FilterDesignerTest, GenerateRatesTest) run for real inside build() and must
pass; the three hardware cases require a physical AD9361/FMComms5 board over
libiio, which an OHOS PC does not have, and are documented as skipped in
notes/manifest/PR body.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file


class Libad9361iioConan(ConanFile):
    name = "libad9361-iio"
    version = "0.3"
    description = "AD9361 transceiver helper library (filter design and clock-chain algorithms)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/analogdevicesinc/libad9361-iio"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Required by the recipe-completeness gate even with an empty patch
        # set; exports any conandata.yml-registered patches.
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libiio/0.25")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        lib = self.dependencies["libiio"]
        libdir = lib.cpp_info.libdirs[0]
        tc = CMakeToolchain(self)
        # Upstream hardcodes set(BUILD_SHARED_LIBS ON CACHE BOOL ...) (no
        # FORCE), forcing a shared build; a command-line/cache variable set
        # through the toolchain takes precedence and yields the static
        # library this package ships.
        # The upstream CMake locates libiio with bare find_library(iio) /
        # find_path(iio.h); hand it the Conan-managed paths directly.
        static = os.path.join(libdir, "libiio.a")
        if os.path.exists(static):
            tc.variables["LIBIIO_LIBRARIES"] = static
        else:
            tc.variables["LIBIIO_LIBRARIES"] = os.path.join(libdir, "libiio.so")
        tc.variables["LIBIIO_INCLUDEDIR"] = lib.cpp_info.includedirs[0]
        tc.variables["BUILD_SHARED_LIBS"] = False
        # Static-build exposure of an upstream test design quirk:
        # gen_rates_test.c embeds its own copy of the linux-driver baseline
        # (linux_calculate_rf_clock_chain) that defines the same strong
        # symbols (RX/TX_MAX/MIN_PATH_RATES) as the library objects. With a
        # dynamic build each side keeps its own copy, but a static link
        # collides. Allow the duplicate definitions for the test executables
        # only; no test logic or assertion is touched.
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--allow-multiple-definition"
        tc.generate()

    def build(self):
        # Applies the (currently empty) conandata patch set; kept as the
        # canonical patch entry point required by the completeness gate.
        apply_conandata_patches(self)

        src = self.source_folder

        # cmake_minimum_required(VERSION 2.8.12) predates the Conan
        # toolchain/dep generators; raise the floor (sources-only change).
        replace_in_file(self, os.path.join(src, "CMakeLists.txt"),
                        "cmake_minimum_required(VERSION 2.8.12)",
                        "cmake_minimum_required(VERSION 3.15)")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Upstream CTest suite (5 add_test cases) runs for real inside
        # build(): the two pure-software algorithm cases must pass. The three
        # hardware cases need a physical AD9361/FMComms5 board over libiio
        # (not present on an OHOS PC) - per-case ledger in notes.md.
        # The test executables link libiio.so (no static libiio build is
        # published); ctest runs under conanbuild, so the runtime search path
        # for libiio and its transitive deps (libxml2 ...) is aggregated from
        # every dependency's lib dir.
        ldpaths = []
        for dep in self.dependencies.values():
            ldpaths.extend(dep.cpp_info.libdirs)
        self.run('LD_LIBRARY_PATH="' + ":".join(ldpaths) + '" '
                 'ctest -R "FilterDesignerTest|GenerateRatesTest" --output-on-failure',
                 cwd=self.build_folder, env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Static-only package: strip any shared-library leftovers.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la") or ".so" in name:
                    os.remove(os.path.join(libdir, name))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["ad9361"]
        # libad9361.a references libiio symbols; propagate to consumers.
        self.cpp_info.requires = ["libiio::libiio"]
