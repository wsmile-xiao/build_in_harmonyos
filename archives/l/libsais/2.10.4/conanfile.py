#!/usr/bin/env python3
"""Conan recipe — libsais 2.10.4 (CMake)"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, rename, rmdir


class LibsaisConan(ConanFile):
    name = "libsais"
    version = "2.10.4"
    description = (
        "Linear-time suffix array (SA), generalized suffix array (GSA), "
        "longest common prefix (LCP), permuted LCP (PLCP), Burrows-Wheeler "
        "transform (BWT) and inverse BWT construction based on induced sorting"
    )
    licenses = "Apache-2.0"
    homepage = "https://github.com/IlyaGrebnov/libsais"
    topics = ("suffix-array", "bwt", "induced-sorting", "string-algorithm")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "openmp": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Install to lib/ (not lib64/) so cpp_info.libdirs matches.
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        # Upstream options (verified against 2.10.4 CMakeLists.txt — these are
        # the ONLY two options the project defines; no SIMD / benchmark /
        # example targets exist). OpenMP off (non-essential on OHOS aarch64).
        tc.variables["LIBSAIS_USE_OPENMP"] = bool(self.options.openmp)
        tc.variables["LIBSAIS_BUILD_SHARED_LIB"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream sets PREFIX "" so the static lib is installed as "libsais.a"
        # (no "lib" prefix). Conan's CMakeDeps find_library(NAMES libsais) looks
        # for "liblibsais.a" on Unix, so rename to match the expected convention.
        libdir = os.path.join(self.package_folder, "lib")
        for fn in ("libsais.a", "libsais.so"):
            src = os.path.join(libdir, fn)
            if os.path.isfile(src):
                rename(self, src, os.path.join(libdir, "lib" + fn))
        # Remove upstream-installed CMake package-config files; Conan generates
        # its own CMakeDeps config (libsais-config.cmake) which must not clash.
        cmake_cfg = os.path.join(self.package_folder, "lib", "cmake", "libsais")
        if os.path.isdir(cmake_cfg):
            rmdir(self, cmake_cfg)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libsais")
        self.cpp_info.set_property("cmake_target_name", "libsais::libsais")
        self.cpp_info.set_property("pkg_config_name", "libsais")
        self.cpp_info.libs = ["libsais"]
