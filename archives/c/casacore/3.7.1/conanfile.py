#!/usr/bin/env python3
"""Conan recipe for casacore 3.7.1 — CMake-based astronomical data processing library.

Casacore is a C++ library for radio astronomy data processing.
Build system: CMake (minimum 3.14).
C++ standard: C++17.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
import json
import os
import subprocess


class CasacoreConan(ConanFile):
    name = "casacore"
    version = "3.7.1"
    description = "Astronomical data processing library for radio astronomy"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/casacore/casacore"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "use_hdf5": [True, False],
        "use_readline": [True, False],
        "use_threads": [True, False],
        "enable_tablelocking": [True, False],
    }
    default_options = {
        "shared": False,
        "use_hdf5": True,
        "use_readline": True,
        "use_threads": True,
        "enable_tablelocking": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("cfitsio/4.6.4")
        self.requires("wcslib/8.4")
        self.requires("fftw/3.3.10")
        self.requires("openblas/0.3.28")
        if self.options.use_hdf5:
            self.requires("hdf5/1.14.6")
        if self.options.use_readline:
            self.requires("readline/8.3")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/2.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sysroot_libdir(self):
        """Locate the OHOS toolchain sysroot library dir via the compiler.

        Casacore's custom find modules (FindCFITSIO/FindWCSLIB/FindPthreads)
        and casa/CMakeLists.txt call find_library(m)/find_library(pthread),
        which fail on OHOS because CMake does not know the SDK sysroot.
        Passing a bare name (e.g. M_LIBRARY="m") makes CMake store it as a
        FILEPATH relative to the build dir, producing "No rule to make
        target 'm'" when linking executables. Instead we resolve the real
        sysroot path from the compiler itself.
        """
        if self.settings.os != "OHOS":
            return None
        try:
            cc_conf = self.conf.get("tools.build:compiler_executables")
            if isinstance(cc_conf, str):
                cc_conf = json.loads(cc_conf)
            cc = (cc_conf or {}).get("c") or "clang"
            res = subprocess.run([cc, "-print-file-name=libm.a"],
                                 capture_output=True, text=True, timeout=30)
            libm = os.path.normpath(res.stdout.strip())
            if res.returncode == 0 and libm.endswith("libm.a") and os.path.isfile(libm):
                return os.path.dirname(libm)
        except Exception:
            pass
        return None

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable Python bindings (not available on OHOS)
        tc.cache_variables["BUILD_PYTHON"] = "OFF"
        tc.cache_variables["BUILD_PYTHON3"] = "OFF"
        # Disable optional features not available on OHOS
        tc.cache_variables["USE_ADIOS2"] = "OFF"
        tc.cache_variables["USE_OPENMP"] = "OFF"
        tc.cache_variables["USE_MPI"] = "OFF"
        tc.cache_variables["USE_STACKTRACE"] = "OFF"
        tc.cache_variables["USE_PCH"] = "OFF"
        tc.cache_variables["BUILD_DYSCO"] = "OFF"
        tc.cache_variables["BUILD_FFTPACK_DEPRECATED"] = "OFF"
        tc.cache_variables["BUILD_DEPRECATED"] = "OFF"
        tc.cache_variables["BUILD_TESTING"] = "OFF"
        # Set module to build all
        tc.cache_variables["MODULE"] = "all"
        # Enable/disable based on options
        tc.cache_variables["USE_HDF5"] = "ON" if self.options.use_hdf5 else "OFF"
        tc.cache_variables["USE_READLINE"] = "ON" if self.options.use_readline else "OFF"
        tc.cache_variables["USE_THREADS"] = "ON" if self.options.use_threads else "OFF"
        tc.cache_variables["ENABLE_TABLELOCKING"] = "ON" if self.options.enable_tablelocking else "OFF"
        # Disable rpath (Conan manages RPATH)
        tc.cache_variables["ENABLE_RPATH"] = "OFF"
        # Shared/static
        tc.cache_variables["ENABLE_SHARED"] = "ON" if self.options.shared else "OFF"
        # Add cmake module path for casacore's custom find modules
        tc.cache_variables["CASA_DEFAULT_ALIGNMENT"] = "32"
        # Disable FFTW3 threads (Conan FFTW package only provides non-threaded)
        tc.cache_variables["FFTW3_DISABLE_THREADS"] = "ON"
        # AIPS_NOLARGEFILE: stop casacore (aipsenv.h/LargeIOFuncDef.h/File.h)
        # from defining _LARGEFILE64_SOURCE and from using the *64 LFS
        # function aliases (fopen64/lseek64/...). OHOS fcntl.h maps those
        # names via "#define open64 open" etc. (clang predefines _GNU_SOURCE),
        # and OHOS/musl off_t is always 64-bit, so the plain functions are
        # equivalent. The open64 *member method* name conflict is handled by
        # patches/0002-undef-open64-to-avoid-musl-macro-conflict.patch.
        tc.preprocessor_definitions["AIPS_NOLARGEFILE"] = None
        # Give CMake the sysroot search paths so casacore's find_library(m)
        # and find_path(pthread.h) resolve to real files (see _sysroot_libdir)
        libdir = self._sysroot_libdir()
        if libdir:
            tc.cache_variables["CMAKE_LIBRARY_PATH"] = libdir
            usr_dir = os.path.dirname(os.path.dirname(libdir))
            incdir = os.path.join(usr_dir, "include")
            if os.path.isdir(incdir):
                tc.cache_variables["CMAKE_INCLUDE_PATH"] = incdir
        # Point custom find modules to Conan package directories
        if "fftw" in self.dependencies:
            fftw_pkg = self.dependencies["fftw"].package_folder
            tc.cache_variables["FFTW3_ROOT_DIR"] = fftw_pkg
        if "hdf5" in self.dependencies:
            hdf5_pkg = self.dependencies["hdf5"].package_folder
            tc.cache_variables["HDF5_ROOT_DIR"] = hdf5_pkg
            tc.cache_variables["HDF5_INCLUDE_DIRS"] = f"{hdf5_pkg}/include"
            tc.cache_variables["HDF5_LIBRARIES"] = f"{hdf5_pkg}/lib/libhdf5.so"
        if "cfitsio" in self.dependencies:
            cfitsio_pkg = self.dependencies["cfitsio"].package_folder
            tc.cache_variables["CFITSIO_ROOT_DIR"] = cfitsio_pkg
        if "wcslib" in self.dependencies:
            wcslib_pkg = self.dependencies["wcslib"].package_folder
            tc.cache_variables["WCSLIB_ROOT_DIR"] = wcslib_pkg
        if "readline" in self.dependencies:
            readline_pkg = self.dependencies["readline"].package_folder
            tc.cache_variables["READLINE_ROOT_DIR"] = readline_pkg
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix FFTW3 find_package: Conan FFTW only provides double precision
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(self, cmakelists,
            "find_package (FFTW3 COMPONENTS single double threads REQUIRED)",
            "find_package (FFTW3 COMPONENTS double REQUIRED)")
        replace_in_file(self, cmakelists,
            "find_package (FFTW3 COMPONENTS single double REQUIRED)",
            "find_package (FFTW3 COMPONENTS double REQUIRED)")
        cmake = CMake(self)
        # Remove -pedantic flag (causes errors with final-on-non-virtual in clang 15)
        replace_in_file(self, cmakelists,
            "-pedantic ", "")
        # Fix clang 15 error: final on non-virtual methods in tables/AlternateMans
        for hdr in ["tables/AlternateMans/AntennaPairStMan.h",
                    "tables/AlternateMans/StokesIStMan.h",
                    "tables/AlternateMans/UvwStMan.h"]:
            hpath = os.path.join(self.source_folder, hdr)
            replace_in_file(self, hpath, " final;", ";", strict=False)
        # open64/open macro conflict is fixed globally via AIPS_NOLARGEFILE
        # preprocessor definition in generate() (see comment there).
        cmake.configure()
        # Fix malloc_trim not available on OHOS (glibc-specific)
        memory_cc = os.path.join(self.source_folder, "casa", "OS", "Memory.cc")
        replace_in_file(self, memory_cc,
            "#elif !defined(AIPS_NO_LEA_MALLOC)",
            "#elif !defined(AIPS_NO_LEA_MALLOC) && defined(__GLIBC__)")
        # casa_scimath_f (Fortran) removal and direct LAPACK/BLAS linking
        # are handled by patches/0003-link-lapack-into-scimath-when-fortran-disabled.patch
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = [
            "casa_casa",
            "casa_mirlib",
            "casa_tables",
            "casa_scimath",
            "casa_measures",
            "casa_meas",
            "casa_fits",
            "casa_ms",
            "casa_msfits",
            "casa_derivedmscal",
            "casa_lattices",
            "casa_coordinates",
            "casa_images",
        ]
        self.cpp_info.set_property("cmake_file_name", "casacore")
        self.cpp_info.set_property("cmake_target_name", "casacore::casacore")
        # System libraries
        self.cpp_info.system_libs = ["dl", "m", "pthread"]
