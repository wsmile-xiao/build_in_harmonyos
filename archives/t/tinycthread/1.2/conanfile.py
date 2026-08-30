#!/usr/bin/env python3
"""Conan recipe for tinycthread — C11 threads API implementation.

tinycthread is a minimalist, portable threading library for C,
closely modeled after the C11 standard.
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class TinycthreadConan(ConanFile):
    name = "tinycthread"
    version = "1.2"
    description = "Small, portable implementation of the C11 threads API"
    license = "Zlib"
    homepage = "https://tinycthread.github.io"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TINYCTHREAD_INSTALL"] = True
        tc.variables["TINYCTHREAD_DISABLE_TESTS"] = False
        tc.variables["TINYCTHREAD_USE_PTHREAD_MUTEX_TIMEDLOCK"] = self.settings.os not in ("OHOS",)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "README.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tinycthread"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
