#!/usr/bin/env python3
"""Conan recipe for hypre 3.1.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class HypreConan(ConanFile):
    name = "hypre"
    version = "3.1.0"
    description = "Scalable linear solvers and multigrid methods"
    license = "Apache-2.0 OR MIT"
    homepage = "https://github.com/hypre-space/hypre"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["HYPRE_ENABLE_MPI"] = False
        toolchain.variables["HYPRE_ENABLE_OPENMP"] = False
        toolchain.variables["HYPRE_ENABLE_FORTRAN"] = False
        toolchain.variables["HYPRE_ENABLE_CUDA"] = False
        toolchain.variables["HYPRE_ENABLE_HIP"] = False
        toolchain.variables["HYPRE_ENABLE_SYCL"] = False
        toolchain.variables["HYPRE_ENABLE_HYPRE_BLAS"] = True
        toolchain.variables["HYPRE_ENABLE_HYPRE_LAPACK"] = True
        toolchain.variables["HYPRE_BUILD_EXAMPLES"] = False
        toolchain.variables["HYPRE_BUILD_TESTS"] = True
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "src"))
        cmake.build()
        if not can_run(self):
            self.output.warning(
                "hypre upstream CTest cannot run in this cross-build "
                "configuration; skipping upstream tests until an OHOS "
                "runner/emulator or native OHOS build is available"
            )
            return
        ctest_env = Environment()
        ctest_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        ctest_env.define("CTEST_PARALLEL_LEVEL", "1")
        with ctest_env.vars(self).apply():
            cmake.test()

    def package(self):
        CMake(self).install()
        for license_file in ("COPYRIGHT", "LICENSE-APACHE", "LICENSE-MIT"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )

    def package_info(self):
        self.cpp_info.libs = ["HYPRE"]
        self.cpp_info.set_property("cmake_file_name", "HYPRE")
        self.cpp_info.set_property("cmake_target_name", "HYPRE::HYPRE")
