#!/usr/bin/env python3
"""Conan recipe for tasmanian 8.2 (Tasmanian Sparse Grids toolkit).

Tasmanian (Oak Ridge National Laboratory) builds adaptively refined sparse
grids for interpolation, quadrature, surrogate modelling and DREAM style
optimization. The package delivers the two upstream libraries
(tasmaniansparsegrid / tasmaniandream), the public headers (C++ and C
interface), the upstream CMake package config and the ``tasgrid`` command
line tool.

The recipe keeps the upstream default feature set: OpenMP, BLAS/LAPACK,
Python, CUDA, HIP, DPC++, MAGMA, Fortran, MPI and SWIG are OFF upstream and
are kept OFF here. Both optional acceleration paths were evaluated on the
device and rejected on evidence (details in notes.md):

* OpenMP: OHOS clang 15 accepts -fopenmp and links libomp, but the produced
  binaries then fail at load time with ``Error loading shared library
  libomp.so`` and 5 of the 14 upstream suites cannot run at all.
* BLAS/LAPACK: the static BLAS/LAPACK archives published for OHOS are built
  with the flang toolchain and do not hand the Fortran runtime over to
  consumers (undefined ``_FortranACharacterCompareScalar1``). With the full
  closure linked the upstream Refinement suite needs 630 s instead of 13 s.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class TasmanianConan(ConanFile):
    name = "tasmanian"
    version = "8.2"
    package_type = "library"
    description = "Adaptive sparse grid toolkit (Tasmanian Sparse Grids) with the tasgrid command line tool"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ORNL/TASMANIAN"
    url = ("https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/"
           "tree/main/archives/t/tasmanian/8.2")
    topics = ("sparse-grid", "interpolation", "quadrature", "optimization", "hpc")

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "%s is not validated for %s" % (self.name, self.settings.os))

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        # Upstream defaults, pinned explicitly so the package id is stable.
        tc.cache_variables["Tasmanian_ENABLE_RECOMMENDED"] = False
        tc.cache_variables["Tasmanian_ENABLE_OPENMP"] = False
        tc.cache_variables["Tasmanian_ENABLE_BLAS"] = False
        tc.cache_variables["Tasmanian_ENABLE_PYTHON"] = False
        tc.cache_variables["Tasmanian_ENABLE_CUDA"] = False
        tc.cache_variables["Tasmanian_ENABLE_MAGMA"] = False
        tc.cache_variables["Tasmanian_ENABLE_HIP"] = False
        tc.cache_variables["Tasmanian_ENABLE_DPCPP"] = False
        tc.cache_variables["Tasmanian_ENABLE_FORTRAN"] = False
        tc.cache_variables["Tasmanian_ENABLE_MPI"] = False
        tc.cache_variables["Tasmanian_ENABLE_SWIG"] = False
        tc.cache_variables["Tasmanian_ENABLE_DOXYGEN"] = False
        if self.settings.os in ("Linux", "OHOS"):
            # E092: CMake has no Platform/HarmonyOS module.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            # Upstream registers its whole regression matrix with ctest (14
            # suites: SparseGrids 10 / DREAM 3 / Addons 1). Running it keeps the
            # package validated exactly like the upstream CI does.
            jobs = max(1, min(4, os.cpu_count() or 1))
            self.run("ctest --output-on-failure -j%d" % jobs, cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tasmaniansparsegrid", "tasmaniandream"]
        # The package also ships the upstream `tasgrid` command line tool,
        # so it is declared as a CLI package: the software level
        # archives/t/tasmanian/commands.json declares that tool (R38).
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        if not self.options.shared:
            # The libraries are built from C++ sources: a consumer of the
            # static archives also needs the C++ runtime (same handling as
            # belr/5.3.105 and bctoolbox/5.3.115).
            self.cpp_info.system_libs.append("c++")
        self.cpp_info.set_property("cmake_file_name", "Tasmanian")
        self.cpp_info.set_property("cmake_target_name", "Tasmanian::Tasmanian")
