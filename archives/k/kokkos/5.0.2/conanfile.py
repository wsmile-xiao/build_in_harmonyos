#!/usr/bin/env python3
"""Conan recipe for Kokkos 5.0.2."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    collect_libs,
    export_conandata_patches,
    get,
    mkdir,
)


class KokkosConan(ConanFile):
    name = "kokkos"
    version = "5.0.2"
    description = "C++ performance-portability programming model"
    # The 5.0.2 source archive's root LICENSE declares Apache-2.0 with LLVM Exceptions.
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://kokkos.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_CXX_STANDARD"] = "20"
        toolchain.variables["Kokkos_ENABLE_SERIAL"] = True
        toolchain.variables["Kokkos_ENABLE_OPENMP"] = False
        toolchain.variables["Kokkos_ENABLE_THREADS"] = False
        toolchain.variables["Kokkos_ENABLE_CUDA"] = False
        toolchain.variables["Kokkos_ENABLE_HIP"] = False
        toolchain.variables["Kokkos_ENABLE_SYCL"] = False
        toolchain.variables["Kokkos_ENABLE_OPENACC"] = False
        toolchain.variables["Kokkos_ENABLE_OPENMPTARGET"] = False
        toolchain.variables["Kokkos_ENABLE_TESTS"] = True
        toolchain.variables["Kokkos_ENABLE_HEADER_SELF_CONTAINMENT_TESTS"] = False
        toolchain.variables["Kokkos_ENABLE_EXAMPLES"] = False
        toolchain.variables["Kokkos_ENABLE_BENCHMARKS"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            gtest_tmpdir = os.path.join(self.build_folder, "gtest-tmp")
            mkdir(self, gtest_tmpdir)
            ctest_env = Environment()
            ctest_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
            ctest_env.define("CTEST_PARALLEL_LEVEL", "1")
            ctest_env.define("TEST_TMPDIR", gtest_tmpdir)
            ctest_env.define("TMPDIR", gtest_tmpdir)
            with ctest_env.vars(self).apply():
                cmake.test()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "Kokkos")
        self.cpp_info.set_property("cmake_target_name", "Kokkos::kokkos")
