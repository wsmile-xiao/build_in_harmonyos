#!/usr/bin/env python3
"""Conan recipe for foonathan/memory 0.7-4 on OpenHarmony."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)


class MemoryConan(ConanFile):
    name = "memory"
    version = "0.7-4"
    description = "STL-compatible C++ memory allocator library (foonathan/memory)"
    license = "Zlib"
    homepage = "https://github.com/foonathan/memory"
    url = "https://github.com/foonathan/memory"
    topics = ("memory", "allocator", "STL", "RawAllocator")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream 0.7-4 test suite uses doctest, which the unpatched build
        # fetches from the network via FetchContent; the patched build uses
        # find_package(doctest) instead.
        self.requires("doctest/2.5.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is validated for Linux/OHOS, not {self.settings.os}"
            )
        check_min_cppstd(self, 11)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = 11
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["FOONATHAN_MEMORY_BUILD_EXAMPLES"] = False
        # The upstream doctest/CTest suite is part of the required validation.
        tc.variables["FOONATHAN_MEMORY_BUILD_TESTS"] = True
        tc.variables["FOONATHAN_MEMORY_BUILD_TOOLS"] = True
        tc.variables["FOONATHAN_MEMORY_CHECK_ALLOCATION_SIZE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official doctest/CTest suite (42 TEST_CASE).
        cmake.test()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        # Conan's CMakeDeps supplies the consumer config; the upstream export
        # contains absolute target paths and is not needed here.
        rmdir(self, os.path.join(self.package_folder, "lib", "foonathan_memory", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "foonathan_memory")
        self.cpp_info.set_property("cmake_target_name", "foonathan_memory")
        self.cpp_info.libs = collect_libs(self)
