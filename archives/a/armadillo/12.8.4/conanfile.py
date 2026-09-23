#!/usr/bin/env python3
"""Conan recipe for the Armadillo C++ linear algebra library.

Armadillo provides matrix maths with a Matlab-like API.  The library
builds a thin wrapper (libarmadillo) around header-only internals.
BLAS/LAPACK are provided by OpenBLAS for full linear algebra
functionality (solve, inv, eig_sym, svd, etc.).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ArmadilloConan(ConanFile):
    name = "armadillo"
    version = "12.8.4"
    description = "High-quality C++ linear algebra library with Matlab-like syntax"
    license = "Apache-2.0"
    homepage = "https://arma.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # OpenBLAS provides both BLAS and LAPACK for full linear algebra
        self.requires("openblas/0.3.34")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("armadillo is supported only on Linux/OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        # OpenBLAS provides both BLAS and LAPACK
        tc.variables["OPENBLAS_PROVIDES_LAPACK"] = True
        # Avoid FlexBLAS detection on OHOS/musl
        tc.variables["ALLOW_FLEXIBLAS_LINUX"] = False
        # HDF5 not needed
        tc.variables["DETECT_HDF5"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Armadillo")
        self.cpp_info.set_property("cmake_target_name", "Armadillo::Armadillo")
        self.cpp_info.set_property("pkg_config_name", "armadillo")
        self.cpp_info.libs = ["armadillo"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
