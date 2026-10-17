#!/usr/bin/env python3
"""Conan recipe — flecs 4.1.6 (CMake ECS library).

flecs is a fast entity-component-system library written in C (C99).
Upstream builds with CMake: static (libflecs_static.a) and shared
(libflecs.so) targets. Default: static (R26).
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class FlecsConan(ConanFile):
    name = "flecs"
    version = "4.1.6"
    description = "flecs — fast entity-component-system library in C"
    license = "MIT"
    homepage = "https://www.flecs.dev/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No third-party dependencies besides libc/pthread (upstream links
        # pthread on Linux automatically).
        pass

    def layout(self):
        # The flecs source tree contains a Bazel BUILD file at its root; the
        # default cmake_layout build_folder "build" collides with it on the
        # case-insensitive OHOS/HMDFS filesystem (E193), so use a distinct name.
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Match the selected variant to the library actually built
        if self.options.shared:
            tc.variables["FLECS_STATIC"] = "OFF"
            tc.variables["FLECS_SHARED"] = "ON"
            tc.variables["BUILD_SHARED_LIBS"] = "ON"
        else:
            tc.variables["FLECS_STATIC"] = "ON"
            tc.variables["FLECS_SHARED"] = "OFF"
            tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Upstream tests need the bake submodule repo; not part of the tarball
        tc.variables["FLECS_TESTS"] = "OFF"
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
        if self.options.shared:
            self.cpp_info.libs = ["flecs"]
        else:
            # Upstream static target is named flecs_static (set by
            # add_flecs_target(flecs_static STATIC)); enabling flecs_STATIC
            # keeps FLECS_API empty on non-MSVC, which is the correct
            # visibility for a static consumer.
            self.cpp_info.defines.append("flecs_STATIC")
            self.cpp_info.libs = ["flecs_static"]