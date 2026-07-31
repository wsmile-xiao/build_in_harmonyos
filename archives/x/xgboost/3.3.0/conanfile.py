#!/usr/bin/env python3
"""Conan recipe for xgboost 3.3.0 — CMake project."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.build import check_min_cppstd
import os

required_conan_version = ">=2.0"


class XgboostConan(ConanFile):
    name = "xgboost"
    version = "3.3.0"
    description = "Scalable, Portable and Distributed Gradient Boosting (GBDT, GBRT or GBM) Library"
    license = "Apache-2.0"
    homepage = "https://github.com/dmlc/xgboost"
    url = "https://github.com/dmlc/xgboost"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        check_min_cppstd(self, "17")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Use get() with sha256 verification from conandata.yml
        # CI automatically adds mirror fallback for GitHub URLs
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize HarmonyOS, set to Linux
        if self.settings.os in ("OHOS", "Linux"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # USE_OPENMP=ON by default; OHOS lacks libomp.so shared library
        # so we build without OpenMP on OHOS (static lib only).
        use_omp = self.settings.os != "OHOS"
        tc.variables["USE_OPENMP"] = "ON" if use_omp else "OFF"
        tc.variables["BUILD_STATIC_LIB"] = "ON" if not self.options.shared else "OFF"
        tc.variables["USE_CUDA"] = "OFF"
        tc.variables["BUILD_DEPRECATED_CLI"] = "OFF"
        tc.variables["JVM_BINDINGS"] = "OFF"
        tc.variables["R_LIB"] = "OFF"
        tc.variables["GOOGLE_TEST"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["xgboost", "dmlc"]
        # Only declare OpenMP dependency when built with OpenMP (non-OHOS).
        # OHOS builds without OpenMP, so consumers on OHOS must not link -lomp.
        if self.settings.os != "OHOS":
            self.cpp_info.system_libs = ["omp"]
        self.cpp_info.set_property("cmake_file_name", "xgboost")
        self.cpp_info.set_property("cmake_target_name", "xgboost::xgboost")
        self.cpp_info.set_property("pkg_config_name", "xgboost")