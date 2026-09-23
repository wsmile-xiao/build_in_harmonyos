#!/usr/bin/env python3
"""Conan recipe — libsee 1.1.0 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibseeConan(ConanFile):
    name = "libsee"
    version = "1.1.0"
    package_type = "library"
    license = "Apache-2.0"
    url = "https://github.com/ashvardanian/LibSee"
    homepage = "https://github.com/ashvardanian/LibSee"
    description = "A single-file LD_PRELOAD library for profiling libc calls"
    topics = ("profiling", "libc", "ld-preload")

    settings = "os", "arch", "compiler", "build_type"
    # The upstream project only builds a shared LD_PRELOAD object.
    options = {"shared": [True]}
    default_options = {"shared": True}
    exports_sources = ()

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # The upstream CMakeLists only enables these flags for Linux/Darwin.
        # OHOS must receive them explicitly and has no Conan dependencies.
        from conan.tools.cmake import CMakeToolchain
        tc = CMakeToolchain(self)
        required = "-fPIC -fno-builtin -nostdlib -nostartfiles"
        tc.variables["CMAKE_C_FLAGS"] = required
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-shared"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        copy(self, "libsee.so", src=self.build_folder, dst=self.package_folder + "/lib", keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder + "/licenses", keep_path=False)

    def package_info(self):
        # LibSee intentionally ships no public headers.
        self.cpp_info.includedirs = []
        self.cpp_info.libs = ["see"]
        self.cpp_info.set_property("cmake_file_name", "libsee")
        self.cpp_info.set_property("cmake_target_name", "libsee::libsee")
