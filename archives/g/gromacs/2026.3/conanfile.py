#!/usr/bin/env python3
"""Conan recipe for the GROMACS 2026.3 CPU-only command-line suite."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class GromacsConan(ConanFile):
    name = "gromacs"
    version = "2026.3"
    description = "High-performance molecular dynamics simulation and analysis suite"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gromacs.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("fftw3f/3.3.9")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("GROMACS supports Linux/OHOS builds only")
        if self.settings.arch not in ("armv8", "armv8.3", "armv8.4"):
            raise ConanInvalidConfiguration(
                "The GROMACS HarmonyOS recipe supports AArch64 only"
            )

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _fftw_paths(self):
        package_folder = self.dependencies["fftw3f"].package_folder
        include_dir = os.path.join(package_folder, "include")
        header = os.path.join(include_dir, "fftw3.h")
        candidates = (
            os.path.join(package_folder, "lib", "libfftw3f.so"),
            os.path.join(package_folder, "lib", "libfftw3f.a"),
        )
        library = next((path for path in candidates if os.path.isfile(path)), None)
        if not os.path.isfile(header) or library is None:
            raise ConanInvalidConfiguration(
                "fftw3f/3.3.9 must provide include/fftw3.h and lib/libfftw3f"
            )
        return include_dir, library

    def generate(self):
        fftw_include, fftw_library = self._fftw_paths()
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_TESTING"] = True
        tc.variables["GMX_BUILD_UNITTESTS"] = True
        tc.variables["GMX_TEST_TIMEOUT_FACTOR"] = 5
        tc.variables["GMX_GPU"] = "OFF"
        tc.variables["GMX_MPI"] = False
        tc.variables["GMX_THREAD_MPI"] = True
        tc.variables["GMX_OPENMP"] = False
        tc.variables["GMX_SIMD"] = "ARM_NEON_ASIMD"
        tc.variables["GMX_DOUBLE"] = False
        tc.variables["GMX_FFT_LIBRARY"] = "fftw3"
        tc.variables["GMX_BUILD_OWN_FFTW"] = False
        # FFTW_MEASURE can spend minutes planning each small PME test on OHOS.
        tc.variables["GMX_DISABLE_FFTW_MEASURE"] = True
        tc.variables["FFTWF_INCLUDE_DIR"] = fftw_include.replace("\\", "/")
        tc.variables["FFTWF_LIBRARY"] = fftw_library.replace("\\", "/")
        tc.variables["GMXAPI"] = False
        tc.variables["GMX_USE_HDF5"] = False
        tc.variables["GMX_NNPOT"] = "OFF"
        tc.variables["GMX_USE_PLUMED"] = "OFF"
        tc.variables["GMX_BUILD_HELP"] = False
        tc.variables["GMX_BUILD_MANUAL"] = False
        tc.variables["GMX_PYTHON_PACKAGE"] = False
        tc.variables["GMX_INSTALL_LEGACY_API"] = False
        tc.variables["GMX_BUILD_TARBALL"] = True
        tc.variables["GMX_GIT_VERSION_INFO"] = False
        if self.settings.os == "OHOS":
            tc.variables["HAVE_OPEN_MEMSTREAM"] = False
        tc.generate()

    def _jobs(self):
        configured = self.conf.get("tools.build:jobs", default=20, check_type=int)
        return max(1, min(configured or 20, 20))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        jobs = self._jobs()
        build_jobs = str(jobs)
        test_jobs = str(min(jobs, 4))
        cmake.build(cli_args=["--parallel", build_jobs])
        cmake.build(target="tests", cli_args=["--parallel", build_jobs])
        self.run(
            "ctest --test-dir {} --output-on-failure --parallel {}".format(
                shlex.quote(self.build_folder), test_jobs
            ),
            env=["conanbuild", "conanrun"],
        )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        fftw_libdir = os.path.join(
            self.dependencies["fftw3f"].package_folder, "lib"
        )
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", fftw_libdir)
