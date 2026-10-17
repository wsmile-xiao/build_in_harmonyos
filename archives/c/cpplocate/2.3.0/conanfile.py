#!/usr/bin/env python3
"""Conan recipe — cpplocate 2.3.0 (CMake).

cpplocate is a C++ locator library (with an embedded C library, liblocate).
It is Linux-userland compatible on HarmonyOS: the CompileOptions patch maps
OHOS/HarmonyOS CMAKE_SYSTEM_NAME onto the SYSTEM_LINUX platform code paths.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CpplocateConan(ConanFile):
    name = "cpplocate"
    version = "2.3.0"
    description = "C++ library to locate data, libraries and modules at runtime"
    license = "MIT"
    homepage = "https://github.com/cginternals/cpplocate"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Shared/static switch (upstream BUILD_SHARED_LIBS option)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Tests depend on googletest; upstream test suite is verified locally,
        # not part of the published package.
        tc.variables["OPTION_BUILD_TESTS"] = "OFF"
        # Upstream requires cmake_minimum_required >= 3.0, which CMake 4.x
        # rejects without an explicit policy version minimum. Pass it as a
        # cache variable so it reaches cmake configure.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # liblocate sources are compiled into libcpplocate (self-contained),
        # so consumers link cpplocate only. The standalone liblocate.so is
        # installed by upstream with an empty file prefix ("liblocate.so"),
        # which Conan's CMakeDeps cannot resolve under default lib-prefix
        # naming; we therefore do not declare it as a conan library target.
        self.cpp_info.libs = ["cpplocate"]
