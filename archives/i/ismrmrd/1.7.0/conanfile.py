#!/usr/bin/env python3
"""Conan recipe for ismrmrd 1.7.0 (MIT) — CMake-based library.

Official source: https://github.com/ismrmrd/ismrmrd (tag v1.7.0)
Adaptation notes:
- USE_HDF5_DATASET_SUPPORT=OFF: optional HDF5 dataset I/O disabled; core MR
  data model (acquisitions/images/waveforms/XML) fully functional and matches
  the upstream test scope (upstream unit tests do not cover the HDF5 path).
- Upstream tests use Boost.Test; the published OHOS boost package provides
  headers only (no libboost_unit_test_framework). Boost.Test >= 1.64 is
  header-only, enabled via BOOST_SP_NO_PTHREAD_SETCANCELSTATE (OHOS libc does
  not declare pthread_setcancelstate) and the included/unit_test.hpp variant
  in test_main.cpp (patch tests/).
- BUILD_UTILITIES / BUILD_EXAMPLES = OFF: utilities/examples are not part of
  the published library API and require optional deps (HDF5 etc.).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IsmrmrdConan(ConanFile):
    name = "ismrmrd"
    version = "1.7.0"
    description = "ISMRMRD - ISMRM Raw Data format library for MRI data"
    license = "MIT"
    homepage = "https://ismrmrd.github.io/"
    url = "https://github.com/ismrmrd/ismrmrd"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    requires = "boost/1.84.0"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream CMakeLists declares cmake_minimum_required(2.8.12); CMake >= 4
        # removed compatibility with < 3.5, so pin the policy minimum explicitly.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Optional HDF5 dataset support is disabled; keep the build focused on
        # the core library + tests (see adaptation notes above).
        tc.variables["USE_HDF5_DATASET_SUPPORT"] = "OFF"
        tc.variables["BUILD_UTILITIES"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_TESTS"] = "ON"
        # OHOS libc does not expose pthread_setcancelstate (same as Android);
        # Boost honours BOOST_SP_NO_PTHREAD_SETCANCELSTATE to skip it.
        tc.variables["CMAKE_CXX_FLAGS"] = "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"
        tc.variables["CMAKE_C_FLAGS"] = "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"
        # Headers of the patched tests/CMakeLists.txt find Boost via this var.
        cfg = self.dependencies["boost"].cpp_info
        tc.variables["BOOST_INCLUDE_DIR"] = cfg.includedirs[0]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream declares cmake_minimum_required(2.8.12); CMake >= 4 removed
        # < 3.5 compatibility. The policy minimum must be passed on the command
        # line (toolchain-file cache var is ignored by CMake 4.1 for this check).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # Run upstream unit tests inside the recipe build. The patched
        # tests/CMakeLists.txt defines the 'check' target (test_ismrmrd binary);
        # running it here proves the patched tests are actually instantiated
        # in the conan create path, not only in the exploratory build.
        cmake.build(target="check")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ismrmrd"]
        self.cpp_info.set_property("cmake_file_name", "ismrmrd")
        self.cpp_info.set_property("cmake_target_name", "ismrmrd::ismrmrd")