import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LightGBMConan(ConanFile):
    name = "lightgbm"
    version = "4.6.0"
    description = "A fast, distributed, high performance gradient boosting framework"
    license = "MIT"
    homepage = "https://github.com/microsoft/LightGBM"
    url = "https://github.com/microsoft/LightGBM"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        submodules = {
            "external_libs/compute": ("https://github.com/boostorg/compute/archive/36350b7de849300bd3d72a05d8bf890ca405a014.tar.gz", "compute"),
            "external_libs/eigen": ("https://gitlab.com/libeigen/eigen/-/archive/3147391d946bb4b6c68edd901f2add6ac1f31f8c/eigen-3147391d946bb4b6c68edd901f2add6ac1f31f8c.tar.gz", "eigen"),
            "external_libs/fmt": ("https://github.com/fmtlib/fmt/archive/8303d140a1a11f19b982a9f664bbe59a1ccda3f4.tar.gz", "fmt"),
            "external_libs/fast_double_parser": ("https://github.com/lemire/fast_double_parser/archive/252029ddac664370bdda3f0761675785d92a1573.tar.gz", "fast_double_parser"),
        }
        for destination, (url, filename) in submodules.items():
            get(self, url=url, destination=destination, strip_root=True, filename=f"{filename}.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["USE_OPENMP"] = "OFF"
        tc.variables["USE_MPI"] = "OFF"
        tc.variables["USE_GPU"] = "OFF"
        tc.variables["BUILD_CLI"] = "ON"
        tc.variables["BUILD_CPP_TEST"] = "OFF"
        tc.variables["BUILD_STATIC_LIB"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["_lightgbm"]
        self.cpp_info.bindirs = ["bin"]
