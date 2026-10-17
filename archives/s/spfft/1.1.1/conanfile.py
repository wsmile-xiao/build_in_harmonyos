#!/usr/bin/env python3
"""Conan recipe — SpFFT 1.1.1 (3D FFT transformation library, eth-cscs).

CMake options trimmed for OHOS: MPI off (no MPI runtime), OpenMP off
(declared-libstream conservatism), CUDA/ROCm off (no GPU).  FFTW comes
from the artifact repository as the transform backend.  The upstream
test suite is NOT built: its googletest/CLI11 arrive via CMake
FetchContent from github, which is unreachable from the build host and
unreliable from the CI runner (E299 family), and neither gtest nor
CLI11 is published on the artifact repository to substitute (probed).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class SpfftConan(ConanFile):
    name = "spfft"
    version = "1.1.1"
    description = (
        "SpFFT: 3D FFT transformation library for sparse frequency data"
    )
    license = "BSD-2-Clause"
    homepage = "https://github.com/eth-cscs/SpFFT"
    url = ""  # CI fills this
    topics = ("fft", "3d", "hpc", "sparse")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        self.requires("fftw/3.3.10.3")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if not self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"spfft not validated for {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SPFFT_MPI"] = False
        tc.variables["SPFFT_OMP"] = False
        tc.variables["SPFFT_BUILD_TESTS"] = False
        tc.variables["SPFFT_FFTW_LIB"] = "FFTW"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SPFFT")
        self.cpp_info.libs = ["spfft"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
