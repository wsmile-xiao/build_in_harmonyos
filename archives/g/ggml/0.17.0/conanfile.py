#!/usr/bin/env python3
"""Conan recipe for ggml 0.17.0, built with CMake."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class GgmlConan(ConanFile):
    name = "ggml"
    version = "0.17.0"
    description = "Tensor library for machine learning workloads"
    license = "MIT"
    homepage = "https://github.com/ggerganov/ggml"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "openmp": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "openmp": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_INSTALL_INCLUDEDIR"] = "include"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["GGML_BUILD_EXAMPLES"] = False
        tc.variables["GGML_BUILD_TESTS"] = False
        tc.variables["GGML_CCACHE"] = False
        # The upstream warning set is compiler-ID sensitive and can mix
        # Clang-only flags into C compilation when a profile uses split C/C++
        # compiler executables.
        tc.variables["GGML_ALL_WARNINGS"] = False
        tc.variables["GGML_NATIVE"] = False
        tc.variables["GGML_OPENMP"] = bool(self.options.openmp)
        tc.variables["GGML_CPU"] = True
        tc.generate()

        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ggml")
        self.cpp_info.set_property("cmake_target_name", "ggml::ggml")
        self.cpp_info.set_property("pkg_config_name", "ggml")
        self.cpp_info.libs = ["ggml", "ggml-cpu", "ggml-base"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
