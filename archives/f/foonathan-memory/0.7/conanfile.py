#!/usr/bin/env python3
"""Conan recipe for foonathan/memory 0.7 on OpenHarmony."""
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


class FoonathanMemoryConan(ConanFile):
    name = "foonathan-memory"
    version = "0.7"
    description = "STL-compatible C++ memory allocator library"
    license = "Zlib"
    homepage = "https://github.com/foonathan/memory"
    url = "https://github.com/foonathan/memory"
    topics = ("memory", "allocator", "STL", "RawAllocator")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "with_tools": [True, False],
    }
    default_options = {
        "shared": False,
        "with_tools": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

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
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_CXX_STANDARD"] = 11
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["FOONATHAN_MEMORY_BUILD_EXAMPLES"] = False
        # The upstream CTest target is part of the required validation.
        tc.variables["FOONATHAN_MEMORY_BUILD_TESTS"] = True
        # nodesize_dbg runs on the native OHOS worker and generates the required
        # container_node_sizes_impl.hpp during the build.
        tc.variables["FOONATHAN_MEMORY_BUILD_TOOLS"] = bool(self.options.with_tools)
        tc.variables["FOONATHAN_MEMORY_CHECK_ALLOCATION_SIZE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official Catch2/CTest suite (39 cases, 140870 assertions).
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
        # Conan's CMakeDeps supplies the consumer config.  The upstream export
        # has an absolute-layout-sensitive location and is not needed here.
        rmdir(self, os.path.join(self.package_folder, "lib", "foonathan_memory", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "foonathan_memory")
        self.cpp_info.set_property("cmake_target_name", "foonathan_memory")
        self.cpp_info.libs = collect_libs(self)
        # Upstream installs foonathan/memory below include/foonathan_memory.
        self.cpp_info.includedirs = [os.path.join("include", "foonathan_memory")]
        if self.options.with_tools:
            self.cpp_info.bindirs = ["bin"]
            self.buildenv_info.append_path(
                "PATH", os.path.join(self.package_folder, "bin")
            )
